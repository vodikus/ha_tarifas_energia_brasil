"""Sensor platform for the integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..const import DOMAIN
from ..coordinator import TarifasDeEnergiaBrasilCoordinator
from .config_entities import async_setup_config_entities
from .primary_entities import PRIMARY_ENTITIES, TarifasDeEnergiaBrasilSensor


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the sensor platform."""
    coordinator: TarifasDeEnergiaBrasilCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(TarifasDeEnergiaBrasilSensor(coordinator, description) for description in PRIMARY_ENTITIES)

    await async_setup_config_entities(hass, entry, async_add_entities)
