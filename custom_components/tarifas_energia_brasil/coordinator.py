"""DataUpdateCoordinator para a integração Tarifas de Energia Brasil."""
import logging
from datetime import timedelta, date

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.core import HomeAssistant

from .cloudflare_api import CloudflareAPI
from .database import DatabaseManager
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class TarifasEnergiaCoordinator(DataUpdateCoordinator):
    """Coordenador que busca dados do Cloudflare Worker e mantém cache local."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: CloudflareAPI,
        db: DatabaseManager,
        concessionaria: str,
    ):
        self.api = api
        self.db = db
        self.concessionaria = concessionaria
        self._nocache_flag = False
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(days=1),
        )

    async def _async_update_data(self) -> dict:
        """Busca dados da API ou retorna do cache local em caso de falha."""
        nocache = self._nocache_flag
        try:
            raw = await self.api.async_fetch_tarifas(self.concessionaria, nocache=nocache)
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
                dat_competencia_bandeira=data.get("dat_competencia_bandeira"),
                valor_adicional_bandeira=data.get("valor_adicional_bandeira"),
            )

            _LOGGER.info(
                "Atualização bem-sucedida para '%s'. Bandeira: '%s', Tarifa: %.5f%s.",
                self.concessionaria,
                data["bandeira_vigente"],
                data["tarifa_vigente"],
                " (nocache)" if nocache else "",
            )
            self.update_interval = self._compute_update_interval(data.get("dat_fim_vigencia"))
            return {**data, "api_status": "online"}

        except Exception as err:
            _LOGGER.error("Erro ao buscar dados da API: %s. Tentando cache local.", err)
            cached = await self.db.async_get_latest_tarifa_snapshot(self.concessionaria)
            if cached:
                _LOGGER.warning("Retornando dados do cache local para '%s'.", self.concessionaria)
                self.update_interval = self._compute_update_interval(cached.get("dat_fim_vigencia"))
                dat_comp_bandeira = cached.get("dat_competencia_bandeira")
                return {
                    "bandeira_vigente": cached["bandeira_vigente"],
                    "tarifa_vigente": cached["tarifa_vigente"],
                    "tarifa_base_te": cached.get("tarifa_base_te"),
                    "tarifa_base_tusd": cached.get("tarifa_base_tusd"),
                    "dat_competencia_bandeira": (
                        date.fromisoformat(dat_comp_bandeira) if dat_comp_bandeira else None
                    ),
                    "dat_competencia_tarifa": cached.get("dat_competencia"),
                    "dat_inicio_vigencia": cached.get("dat_inicio_vigencia"),
                    "dat_fim_vigencia": cached.get("dat_fim_vigencia"),
                    "valor_adicional_bandeira": cached.get("valor_adicional_bandeira"),
                    "api_status": "offline",
                    "timestamp": cached["timestamp"],
                }
            raise UpdateFailed(f"Sem dados disponíveis para '{self.concessionaria}': {err}") from err

    def _compute_update_interval(self, dat_fim_vigencia_str: str | None) -> timedelta:
        """Retorna intervalo de polling baseado em dat_fim_vigencia."""
        if dat_fim_vigencia_str is None:
            return timedelta(days=1)
        try:
            dat_fim = date.fromisoformat(dat_fim_vigencia_str[:10])
            if dat_fim <= date.today():
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
        dat_comp_bandeira = bandeira.get("data_competencia")
        return {
            "bandeira_vigente": tarifa.get("bandeira_vigente") or bandeira.get("nome_bandeira"),
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
