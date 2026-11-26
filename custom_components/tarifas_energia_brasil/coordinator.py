"""DataUpdateCoordinator para a integração Tarifas de Energia Brasil."""

import logging
import math
from datetime import timedelta, date

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .cloudflare_api import CloudflareAPI
from .database import DatabaseManager
from .const import (
    DOMAIN,
    POLLING_AUTOMATIC,
    POLLING_FIXED_DAYS,
    STATUS_CACHE,
    STATUS_ONLINE,
)

_LOGGER = logging.getLogger(__name__)


class TarifasEnergiaCoordinator(DataUpdateCoordinator):
    """Coordenador que busca dados do Cloudflare Worker e mantém cache local."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: CloudflareAPI,
        db: DatabaseManager,
        concessionaria: str,
        polling_mode: str = POLLING_AUTOMATIC,
    ):
        self.api = api
        self.db = db
        self.concessionaria = concessionaria
        self.polling_mode = (
            polling_mode
            if polling_mode == POLLING_AUTOMATIC or polling_mode in POLLING_FIXED_DAYS
            else POLLING_AUTOMATIC
        )
        self._nocache_flag = False
        # Diagnóstico em memória (horário local tz-aware do HA). None = ainda não ocorreu.
        self.last_attempt = None
        self.last_success = None
        self.last_error: str | None = None
        initial_days = POLLING_FIXED_DAYS.get(polling_mode, 1)
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(days=initial_days),
        )

    async def _async_update_data(self) -> dict:
        """Busca dados da API ou retorna do cache local em caso de falha."""
        nocache = self._nocache_flag
        self.last_attempt = dt_util.now()
        try:
            raw = await self.api.async_fetch_tarifas(
                self.concessionaria, nocache=nocache
            )
            data = self._parse_api_response(raw)

            dat_competencia = date.fromisoformat(data["dat_inicio_vigencia"])
            await self.db.async_save_tarifa_snapshot(
                concessionaria_nome=self.concessionaria,
                bandeira_vigente=data["bandeira_vigente"],
                tarifa_vigente=data["tarifa_vigente"],
                dat_competencia=dat_competencia,
                api_status="online",
                tarifa_base_te=data.get("tarifa_base_te"),
                tarifa_base_tusd=data.get("tarifa_base_tusd"),
                dat_inicio_vigencia=data.get("dat_inicio_vigencia"),
                dat_fim_vigencia=data.get("dat_fim_vigencia"),
                dat_competencia_bandeira=(
                    data["dat_competencia_bandeira"].isoformat()
                    if data.get("dat_competencia_bandeira")
                    else None
                ),
                valor_adicional_bandeira=data.get("valor_adicional_bandeira"),
            )

            _LOGGER.info(
                "Atualização bem-sucedida para '%s'. Bandeira: '%s', Tarifa: %.5f%s.",
                self.concessionaria,
                data["bandeira_vigente"],
                data["tarifa_vigente"],
                " (nocache)" if nocache else "",
            )
            self._apply_polling_interval(data.get("dat_fim_vigencia"))
            self.last_success = dt_util.now()
            self.last_error = None
            return {
                **data,
                "api_status": STATUS_ONLINE,
                "data_status": STATUS_ONLINE,
                "last_success": self.last_success,
            }

        except Exception as err:
            self.last_error = type(err).__name__
            _LOGGER.error("Erro ao buscar dados da API: %s. Tentando cache local.", err)
            cached = await self.db.async_get_latest_tarifa_snapshot(self.concessionaria)
            if cached:
                _LOGGER.warning(
                    "Retornando dados do cache local para '%s'.", self.concessionaria
                )
                self._apply_polling_interval(cached.get("dat_fim_vigencia"))
                dat_comp_bandeira = cached.get("dat_competencia_bandeira")
                return {
                    "bandeira_vigente": cached["bandeira_vigente"],
                    "tarifa_vigente": cached["tarifa_vigente"],
                    "tarifa_base_te": cached.get("tarifa_base_te"),
                    "tarifa_base_tusd": cached.get("tarifa_base_tusd"),
                    "dat_competencia_bandeira": (
                        date.fromisoformat(dat_comp_bandeira)
                        if dat_comp_bandeira
                        else None
                    ),
                    "dat_competencia_tarifa": cached.get("dat_competencia"),
                    "dat_inicio_vigencia": cached.get("dat_inicio_vigencia"),
                    "dat_fim_vigencia": cached.get("dat_fim_vigencia"),
                    "valor_adicional_bandeira": cached.get("valor_adicional_bandeira"),
                    "api_status": "offline",
                    "data_status": STATUS_CACHE,
                    "timestamp": cached["timestamp"],
                    # Cache não é prova de sucesso atual: last_success fica sem valor.
                    "last_success": None,
                }
            raise UpdateFailed(
                f"Sem dados disponíveis para '{self.concessionaria}': {err}"
            ) from err

    def _apply_polling_interval(self, dat_fim_vigencia_str: str | None) -> None:
        """Aplica o intervalo conforme o modo escolhido nas opções da entrada."""
        if self.polling_mode == POLLING_AUTOMATIC:
            self.update_interval = self._compute_update_interval(dat_fim_vigencia_str)
        else:
            self.update_interval = timedelta(days=POLLING_FIXED_DAYS[self.polling_mode])

    def _compute_update_interval(self, dat_fim_vigencia_str: str | None) -> timedelta:
        """Retorna intervalo de polling baseado em dat_fim_vigencia (modo automático)."""
        if dat_fim_vigencia_str is None:
            return timedelta(days=1)
        try:
            dat_fim = date.fromisoformat(dat_fim_vigencia_str[:10])
            if dat_fim <= dt_util.now().date():
                return timedelta(days=1)
            return timedelta(weeks=1)
        except (ValueError, TypeError):
            return timedelta(days=1)

    async def async_force_refresh_nocache(self) -> None:
        """Força uma atualização ignorando o cache do Cloudflare Worker."""
        self._nocache_flag = True
        try:
            await self.async_refresh()
        finally:
            self._nocache_flag = False

    @staticmethod
    def _parse_api_response(raw: dict) -> dict:
        """Mapeia a resposta da API Cloudflare para o dict interno do coordinator."""
        bandeira = raw.get("bandeira_tarifaria", {})
        tarifa = raw.get("tarifa", {})
        # Uma resposta HTTP não é uma leitura válida se não há preço/identidade temporal.
        price = tarifa.get("tarifa_vigente")
        if (
            isinstance(price, bool)
            or not isinstance(price, (int, float))
            or not math.isfinite(price)
            or price <= 0
        ):
            raise ValueError("Tarifa inválida na resposta")
        if not (tarifa.get("bandeira_vigente") or bandeira.get("nome_bandeira")):
            raise ValueError("Bandeira ausente na resposta")
        inicio = date.fromisoformat(tarifa["dat_inicio_vigencia"])
        fim = date.fromisoformat(tarifa["dat_fim_vigencia"])
        if fim < inicio:
            raise ValueError("Vigência inválida na resposta")
        dat_comp_bandeira = bandeira.get("data_competencia")
        return {
            "bandeira_vigente": tarifa.get("bandeira_vigente")
            or bandeira.get("nome_bandeira"),
            "tarifa_vigente": tarifa.get("tarifa_vigente"),
            "tarifa_base_te": tarifa.get("tarifa_base_te"),
            "tarifa_base_tusd": tarifa.get("tarifa_base_tusd"),
            "dat_competencia_bandeira": (
                date.fromisoformat(dat_comp_bandeira) if dat_comp_bandeira else None
            ),
            "dat_competencia_tarifa": tarifa.get("dat_inicio_vigencia"),
            "dat_inicio_vigencia": tarifa.get("dat_inicio_vigencia"),
            "dat_fim_vigencia": tarifa.get("dat_fim_vigencia"),
            "valor_adicional_bandeira": bandeira.get("valor_adicional"),
            "timestamp": tarifa.get("timestamp"),
        }
