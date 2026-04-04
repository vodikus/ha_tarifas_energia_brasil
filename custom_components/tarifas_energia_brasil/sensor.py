"""Define as entidades de sensor para a integração Tarifas de Energia Brasil."""
import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
)
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
    """Configura as entidades de sensor a partir de uma entrada de configuração."""
    coordinator: TarifasEnergiaCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        TarifaVigenteSensor(coordinator, entry),
        BandeiraVigenteSensor(coordinator, entry),
        DataCompetenciaBandeiraSensor(coordinator, entry),
        DataCompetenciaTarifaSensor(coordinator, entry),
        UltimaAtualizacaoSensor(coordinator, entry),
    ]

    async_add_entities(entities)


class TarifasEnergiaBaseSensor(CoordinatorEntity[TarifasEnergiaCoordinator], SensorEntity):
    """Classe base para os sensores da integração."""

    def __init__(self, coordinator: TarifasEnergiaCoordinator, entry: ConfigEntry):
        """Inicializa o sensor base, recebendo a ConfigEntry."""
        super().__init__(coordinator)
        self.entry = entry
        self._attr_has_entity_name = True

    @property
    def device_info(self):
        """Retorna as informações do dispositivo, usando o entry_id como identificador."""
        concessionaria_nome = self.entry.data[CONF_CONCESSIONARIA]
        return {
            "identifiers": {(DOMAIN, self.entry.entry_id)},
            "name": f"Tarifas {concessionaria_nome}",
            "manufacturer": "ANEEL",
            "model": "Tarifas de Energia Elétrica",
            "entry_type": "service",
        }


class TarifaVigenteSensor(TarifasEnergiaBaseSensor):
    """Sensor que representa o valor da tarifa vigente."""

    _attr_name = "Tarifa Vigente"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_icon = "mdi:cash-multiple"
    _attr_native_unit_of_measurement = "R$/kWh"

    def __init__(self, coordinator: TarifasEnergiaCoordinator, entry: ConfigEntry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{self.entry.entry_id}_tarifa_vigente"

    @property
    def native_value(self) -> float | None:
        if self.coordinator.data:
            return self.coordinator.data.get("tarifa_vigente")
        return None


class BandeiraVigenteSensor(TarifasEnergiaBaseSensor):
    """Sensor que representa qual bandeira tarifária está vigente."""

    _attr_name = "Bandeira Vigente"
    _attr_icon = "mdi:flag"

    def __init__(self, coordinator: TarifasEnergiaCoordinator, entry: ConfigEntry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{self.entry.entry_id}_bandeira_vigente"

    @property
    def native_value(self) -> str | None:
        if self.coordinator.data:
            return self.coordinator.data.get("bandeira_vigente")
        return None


class DataCompetenciaBandeiraSensor(TarifasEnergiaBaseSensor):
    """Sensor que exibe a data de competência da bandeira tarifária (tabela bandeiras_tarifarias)."""

    _attr_name = "Data Competência Bandeira"
    _attr_device_class = SensorDeviceClass.DATE
    _attr_icon = "mdi:calendar-star"

    def __init__(self, coordinator: TarifasEnergiaCoordinator, entry: ConfigEntry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{self.entry.entry_id}_dat_competencia_bandeira"

    @property
    def native_value(self):
        if self.coordinator.data:
            return self.coordinator.data.get("dat_competencia_bandeira")
        return None


class DataCompetenciaTarifaSensor(TarifasEnergiaBaseSensor):
    """Sensor que exibe a data de competência da tarifa vigente (tabela historico_tarifas)."""

    _attr_name = "Data Competência Tarifa"
    _attr_device_class = SensorDeviceClass.DATE
    _attr_icon = "mdi:calendar-check"

    def __init__(self, coordinator: TarifasEnergiaCoordinator, entry: ConfigEntry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{self.entry.entry_id}_dat_competencia_tarifa"

    @property
    def native_value(self):
        if self.coordinator.data:
            val = self.coordinator.data.get("dat_competencia_tarifa")
            if isinstance(val, str):
                from datetime import date
                return date.fromisoformat(val[:10])
            return val
        return None


class UltimaAtualizacaoSensor(TarifasEnergiaBaseSensor):
    """Sensor que exibe o timestamp da última atualização salva."""

    _attr_name = "Última Atualização"
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator: TarifasEnergiaCoordinator, entry: ConfigEntry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{self.entry.entry_id}_ultima_atualizacao"

    @property
    def native_value(self) -> str | None:
        if self.coordinator.data:
            return self.coordinator.data.get("timestamp")
        return None

