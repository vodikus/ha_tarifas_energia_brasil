"""A integração Tarifas de Energia Brasil."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, CONF_CONCESSIONARIA, SERVICE_ATUALIZAR
from .database import DatabaseManager
from .cloudflare_api import CloudflareAPI
from .coordinator import TarifasEnergiaCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "button"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configura a integração a partir de uma entrada de configuração."""
    hass.data.setdefault(DOMAIN, {})

    concessionaria_nome = entry.data[CONF_CONCESSIONARIA]

    db_path = hass.config.path(f"{DOMAIN}.sqlite")
    db_manager = DatabaseManager(hass, db_path)
    await db_manager.async_setup_database()

    session = async_get_clientsession(hass)
    api_client = CloudflareAPI(hass, session)
    coordinator = TarifasEnergiaCoordinator(hass, api_client, db_manager, concessionaria_nome)

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def _handle_atualizar_tarifas(call: ServiceCall) -> None:
        entry_id = call.data.get("entry_id", entry.entry_id)
        coord: TarifasEnergiaCoordinator | None = hass.data[DOMAIN].get(entry_id)
        if coord:
            await coord.async_force_refresh_nocache()
        else:
            _LOGGER.warning("Serviço atualizar_tarifas: entry_id '%s' não encontrado.", entry_id)

    hass.services.async_register(DOMAIN, SERVICE_ATUALIZAR, _handle_atualizar_tarifas)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Descarrega uma entrada de configuração."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
