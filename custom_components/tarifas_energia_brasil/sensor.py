"""Define as entidades de sensor para a integração Tarifas de Energia Brasil."""
import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
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

    # Passa a entrada de configuração (entry) inteira para os sensores
    # para garantir um vínculo forte e único.
    entities = [
        TarifaVigenteSensor(coordinator, entry),
        BandeiraVigenteSensor(coordinator, entry),
        ApiStatusSensor(coordinator, entry),
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
            # Usa o entry_id para um identificador único e estável para o dispositivo.
            # Esta é a mudança principal para garantir que cada entrada crie um novo dispositivo.
            "identifiers": {(DOMAIN, self.entry.entry_id)},
            "name": f"Tarifas {concessionaria_nome}",
            "manufacturer": "ANEEL",
            "model": "Tarifas de Energia Elétrica",
            "entry_type": "service",
        }


# Demais sensores (TarifaVigenteSensor, BandeiraVigenteSensor) permanecem aqui...

# Sensor de status da API deve ser definido após a classe base
class ApiStatusSensor(TarifasEnergiaBaseSensor):
    """Sensor que indica o status da API (online/offline)."""
    _attr_name = "Conexão com a Aneel"
    _attr_icon = "mdi:cloud-check"

    def __init__(self, coordinator: TarifasEnergiaCoordinator, entry: ConfigEntry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{self.entry.entry_id}_api_status"
        self._attr_friendly_name = "API Aneel"

    @property
    def native_value(self) -> str:
        # O status deve ser passado pelo coordinator.data
        if self.coordinator.data and "api_status" in self.coordinator.data:
            return self.coordinator.data["api_status"]
        return "desconhecido"


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
            # Usa o entry_id para um identificador único e estável para o dispositivo.
            # Esta é a mudança principal para garantir que cada entrada crie um novo dispositivo.
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
    # A linha abaixo foi removida para corrigir o erro de incompatibilidade.
    # Um sensor 'monetary' não pode ter a state_class 'measurement'.
    # _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:cash-multiple"
    _attr_native_unit_of_measurement = "R$/kWh"

    def __init__(self, coordinator: TarifasEnergiaCoordinator, entry: ConfigEntry):
        """Inicializa o sensor de tarifa vigente."""
        super().__init__(coordinator, entry)
        # Garante um ID único estável para a entidade, vinculado ao entry_id.
        self._attr_unique_id = f"{self.entry.entry_id}_tarifa_vigente"

    @property
    def native_value(self) -> float | None:
        """Retorna o valor da tarifa correspondente à bandeira vigente ou o valor salvo."""
        if not self.coordinator.data:
            return None

        bandeira = self.coordinator.data.get("bandeira_vigente")
        tarifas = self.coordinator.data.get("tarifas")

        if bandeira and tarifas:
            return tarifas.get(bandeira) / 1000

        # Fallback: se não houver tarifas, usa o campo tarifa_vigente salvo
        if "tarifa_vigente" in self.coordinator.data:
            return self.coordinator.data["tarifa_vigente"]

        return None


class BandeiraVigenteSensor(TarifasEnergiaBaseSensor):
    """Sensor que representa qual bandeira tarifária está vigente."""

    _attr_name = "Bandeira Vigente"
    _attr_icon = "mdi:flag"

    def __init__(self, coordinator: TarifasEnergiaCoordinator, entry: ConfigEntry):
        """Inicializa o sensor da bandeira vigente."""
        super().__init__(coordinator, entry)
        # Garante um ID único estável para a entidade, vinculado ao entry_id.
        self._attr_unique_id = f"{self.entry.entry_id}_bandeira_vigente"

    @property
    def native_value(self) -> str | None:
        """Retorna o nome da bandeira tarifária vigente."""
        if self.coordinator.data:
            return self.coordinator.data.get("bandeira_vigente")
        return None


class UltimaAtualizacaoSensor(TarifasEnergiaBaseSensor):
    """Sensor que exibe o timestamp da última atualização salva."""

    _attr_name = "Última Atualização"
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator: TarifasEnergiaCoordinator, entry: ConfigEntry):
        """Inicializa o sensor da última atualização."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{self.entry.entry_id}_ultima_atualizacao"

    @property
    def native_value(self) -> str | None:
        """Retorna o timestamp vindo de last_data.json."""
        if self.coordinator.data:
            return self.coordinator.data.get("timestamp")
        return None

