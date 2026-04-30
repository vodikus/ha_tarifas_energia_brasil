"""Core DataUpdateCoordinator implementation."""

from datetime import date, timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from ..api import TarifasDeEnergiaBrasilAPI
from ..const import CONF_CONCESSIONARIA, CONF_MODO_IMPOSTOS, DOMAIN, MODO_IMPOSTOS_AUTOMATICO
from ..utils.database import DatabaseManager
from ..utils.scrapers import get_scraper
from .data_processing import process_coordinator_data
from .error_handling import handle_coordinator_errors

_LOGGER = logging.getLogger(__name__)


class TarifasDeEnergiaBrasilCoordinator(DataUpdateCoordinator):
    """Coordenador para buscar e gerenciar os dados de tarifas e faturas."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self.entry = entry
        self.concessionaria = entry.data[CONF_CONCESSIONARIA]

        db_path = hass.config.path(f"{DOMAIN}.sqlite")
        self.db = DatabaseManager(hass, db_path)
        self.session = async_get_clientsession(hass)
        self.api = TarifasDeEnergiaBrasilAPI(hass, self.session, self.db)

        self.last_api_fetch = None

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=30),
        )

    @handle_coordinator_errors
    async def _async_update_data(self) -> dict:
        """Busca os dados mais recentes."""
        await self.db.async_setup_database()
        hoje = date.today()

        # 1. Tenta atualizar dados externos (ANEEL / Scrapers) no máximo 1x por dia
        if self.last_api_fetch != hoje:
            await self._update_external_data(hoje)

        # 2. Carrega o snapshot mais recente
        snapshot = await self.db.async_get_latest_tarifa_snapshot(self.concessionaria)
        if not snapshot:
            raise UpdateFailed("Sem dados locais ou remotos de tarifa.")

        # 3. Carrega dados locais (saldos anteriores)
        local_data = await self.db.async_get_local_data(self.entry.entry_id)

        # 4. Processa os dados (cálculos de fatura, saldos, etc.)
        processed_data, local_data_updated = process_coordinator_data(self.hass, self.entry, snapshot, local_data)

        # 5. Salva saldo atualizado localmente
        await self.db.async_set_local_data(self.entry.entry_id, local_data_updated)

        return processed_data

    async def _update_external_data(self, hoje: date):
        """Busca dados da ANEEL e Scrapers."""
        await self.api.async_preload_latest_bandeira_csv()

        bandeira_vigente, valor_adicional, dat_comp = await self.api.async_get_bandeira_vigente(hoje) or (
            "Bandeira Verde",
            0.0,
            hoje,
        )
        tarifas_base = await self.api.async_fetch_tarifas_base(self.concessionaria)

        if tarifas_base:
            impostos = {}
            if self.entry.options.get(CONF_MODO_IMPOSTOS) == MODO_IMPOSTOS_AUTOMATICO:
                scraper = get_scraper(self.concessionaria, self.session)
                if scraper:
                    impostos = await scraper.async_get_impostos() or {}

            await self.db.async_save_tarifa_snapshot(
                self.concessionaria,
                bandeira_vigente,
                tarifas_base["te"],
                tarifas_base["tusd"] + valor_adicional,
                dat_comp,
                "online",
                impostos,
            )
            self.last_api_fetch = hoje
        else:
            _LOGGER.warning("Falha na ANEEL. Usando snapshot offline.")
