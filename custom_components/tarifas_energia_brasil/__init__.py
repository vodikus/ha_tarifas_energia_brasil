"""Configura a integração Tarifas de Energia Brasil."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configura Tarifas Energia Brasil a partir de uma entrada de configuração."""
    hass.data.setdefault(DOMAIN, {})

    # Import local deferido para evitar loops circulares
    from .coordinator import TarifasDeEnergiaBrasilCoordinator

    coordinator = TarifasDeEnergiaBrasilCoordinator(hass, entry)

    # A primeira atualização dos dados para registrar na inicialização
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Configura as plataformas (sensores)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Registra o listener de atualização para o Options Flow
    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Manipula a atualização de opções."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Descarrega a integração."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
