"""Entidade botão para forçar atualização de tarifas via API Cloudflare."""
import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_CONCESSIONARIA
from .coordinator import TarifasEnergiaCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: TarifasEnergiaCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AtualizarTarifasButton(coordinator, entry)])


class AtualizarTarifasButton(CoordinatorEntity[TarifasEnergiaCoordinator], ButtonEntity):
    """Botão que força uma requisição à API com nocache=true."""

    _attr_name = "Atualizar Tarifas"
    _attr_icon = "mdi:refresh"

    def __init__(self, coordinator: TarifasEnergiaCoordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_atualizar_tarifas"
        self._attr_has_entity_name = True

    @property
    def device_info(self):
        concessionaria_nome = self.entry.data[CONF_CONCESSIONARIA]
        return {
            "identifiers": {(DOMAIN, self.entry.entry_id)},
            "name": f"Tarifas {concessionaria_nome}",
            "manufacturer": "ANEEL",
            "model": "Tarifas de Energia Elétrica",
            "entry_type": "service",
        }

    async def async_press(self) -> None:
        """Dispara atualização forçada ignorando o cache do Cloudflare Worker."""
        _LOGGER.info("Botão pressionado: forçando atualização com nocache=true para '%s'.", self.entry.data[CONF_CONCESSIONARIA])
        await self.coordinator.async_force_refresh_nocache()
