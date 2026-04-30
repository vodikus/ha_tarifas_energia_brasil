"""Base entity classes for the integration."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import CONF_CONCESSIONARIA, DOMAIN
from ..coordinator import TarifasDeEnergiaBrasilCoordinator


class TarifasDeEnergiaBrasilEntity(CoordinatorEntity[TarifasDeEnergiaBrasilCoordinator]):
    """Base class for Tarifas de Energia Brasil entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: TarifasDeEnergiaBrasilCoordinator, description: EntityDescription) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self.entry = coordinator.entry

        self._attr_unique_id = f"{self.entry.entry_id}_{description.key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        concessionaria_nome = self.entry.data.get(CONF_CONCESSIONARIA, "Desconhecida")
        return DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            name=f"Tarifas {concessionaria_nome}",
            manufacturer="ANEEL / Extensão",
            model="Tarifas e Gestão de Fatura",
            entry_type="service",
        )
