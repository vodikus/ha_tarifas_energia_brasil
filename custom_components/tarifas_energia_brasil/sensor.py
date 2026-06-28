"""Define as entidades de sensor para a integração Tarifas de Energia Brasil."""
import logging
from datetime import date

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
        DataInicioCompetenciaSensor(coordinator, entry),
        DataFimCompetenciaSensor(coordinator, entry),
        UltimaAtualizacaoSensor(coordinator, entry),
    ]

    async_add_entities(entities)


class TarifasEnergiaBaseSensor(CoordinatorEntity[TarifasEnergiaCoordinator], SensorEntity):
    """Classe base para os sensores da integração."""

    def __init__(self, coordinator: TarifasEnergiaCoordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self.entry = entry
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

    @property
    def extra_state_attributes(self) -> dict | None:
        if not self.coordinator.data:
            return None
        d = self.coordinator.data
        return {
            "tarifa_base_te": d.get("tarifa_base_te"),
            "tarifa_base_tusd": d.get("tarifa_base_tusd"),
            "valor_adicional_bandeira": d.get("valor_adicional_bandeira"),
            "api_status": d.get("api_status"),
        }


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
    """Sensor que exibe a data de competência da bandeira tarifária."""

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


class DataInicioCompetenciaSensor(TarifasEnergiaBaseSensor):
    """Sensor que exibe a data de início da vigência da tarifa."""

    _attr_name = "Data Início Vigência"
    _attr_device_class = SensorDeviceClass.DATE
    _attr_icon = "mdi:calendar-arrow-right"

    def __init__(self, coordinator: TarifasEnergiaCoordinator, entry: ConfigEntry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{self.entry.entry_id}_dat_inicio_vigencia"

    @property
    def native_value(self) -> date | None:
        if self.coordinator.data:
            val = self.coordinator.data.get("dat_inicio_vigencia")
            if isinstance(val, str):
                return date.fromisoformat(val[:10])
        return None


class DataFimCompetenciaSensor(TarifasEnergiaBaseSensor):
    """Sensor que exibe a data de fim da vigência da tarifa."""

    _attr_name = "Data Fim Vigência"
    _attr_device_class = SensorDeviceClass.DATE
    _attr_icon = "mdi:calendar-arrow-left"

    def __init__(self, coordinator: TarifasEnergiaCoordinator, entry: ConfigEntry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{self.entry.entry_id}_dat_fim_vigencia"

    @property
    def native_value(self) -> date | None:
        if self.coordinator.data:
            val = self.coordinator.data.get("dat_fim_vigencia")
            if isinstance(val, str):
                return date.fromisoformat(val[:10])
        return None


class UltimaAtualizacaoSensor(TarifasEnergiaBaseSensor):
    """Sensor que exibe o timestamp da última atualização."""

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
