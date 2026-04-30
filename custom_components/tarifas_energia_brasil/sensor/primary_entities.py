"""Primary sensor entities."""

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass

from ..coordinator import TarifasDeEnergiaBrasilCoordinator
from ..entity import TarifasDeEnergiaBrasilEntity

PRIMARY_ENTITIES: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="tarifa_vigente_final",
        name="Tarifa Vigente",
        device_class=SensorDeviceClass.MONETARY,
        icon="mdi:cash-multiple",
        native_unit_of_measurement="R$/kWh",
        state_class=SensorStateClass.TOTAL,
    ),
    SensorEntityDescription(
        key="bandeira_vigente",
        name="Bandeira Vigente",
        icon="mdi:flag",
    ),
    SensorEntityDescription(
        key="api_status",
        name="Conexão da API",
        icon="mdi:cloud-check",
    ),
    SensorEntityDescription(
        key="timestamp",
        name="Última Atualização Local",
        icon="mdi:calendar-clock",
    ),
    SensorEntityDescription(
        key="tarifa_base_aneel",
        name="Tarifa Base ANEEL (Sem Impostos)",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="R$/kWh",
    ),
    SensorEntityDescription(
        key="aliquota_icms",
        name="Alíquota ICMS",
        icon="mdi:percent",
        native_unit_of_measurement="%",
    ),
    SensorEntityDescription(
        key="aliquota_pis",
        name="Alíquota PIS",
        icon="mdi:percent",
        native_unit_of_measurement="%",
    ),
    SensorEntityDescription(
        key="aliquota_cofins",
        name="Alíquota COFINS",
        icon="mdi:percent",
        native_unit_of_measurement="%",
    ),
    SensorEntityDescription(
        key="fatura_estimada_r",
        name="Estimativa Fatura Atual",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="R$",
    ),
    SensorEntityDescription(
        key="saldo_creditos_kwh",
        name="Saldo de Créditos (SCEE)",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="kWh",
    ),
    SensorEntityDescription(
        key="energia_compensada_kwh",
        name="Energia Compensada",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="kWh",
    ),
    SensorEntityDescription(
        key="energia_nao_compensada_kwh",
        name="Energia Não Compensada",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="kWh",
    ),
    SensorEntityDescription(
        key="auto_consumo_estimado",
        name="Auto Consumo Estimado",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="kWh",
    ),
    SensorEntityDescription(
        key="fio_b_final",
        name="Fio B Compensado (Custo Efetivo)",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="R$/kWh",
    ),
    SensorEntityDescription(
        key="consumo_minimo_kwh",
        name="Consumo Mínimo Faturável",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="kWh",
        icon="mdi:lightning-bolt-outline",
    ),
)


class TarifasDeEnergiaBrasilSensor(SensorEntity, TarifasDeEnergiaBrasilEntity):
    """Sensor representation."""

    entity_description: SensorEntityDescription

    def __init__(self, coordinator: TarifasDeEnergiaBrasilCoordinator, description: SensorEntityDescription) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, description)

    @property
    def native_value(self) -> float | str | None:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None

        val = self.coordinator.data.get(self.entity_description.key)

        # Formatação de casas decimais baseada no tipo de sensor
        if val is not None and isinstance(val, (float, int)):
            if (
                self.entity_description.device_class == SensorDeviceClass.MONETARY
                and self.entity_description.native_unit_of_measurement == "R$/kWh"
            ):
                return round(val, 6)
            if (
                self.entity_description.device_class == SensorDeviceClass.MONETARY
                or self.entity_description.native_unit_of_measurement == "%"
                or self.entity_description.device_class == SensorDeviceClass.ENERGY
            ):
                return round(val, 2)

        return val

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return (
            super().available
            and self.coordinator.data is not None
            and self.entity_description.key in self.coordinator.data
        )
