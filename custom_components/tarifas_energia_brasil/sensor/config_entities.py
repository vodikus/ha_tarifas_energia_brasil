"""Sensor entities that expose configuration options as HA entities.

These sensors read directly from the config entry options/data, not from
coordinator.data, so they reflect the current integration configuration and
are always available as long as the integration is loaded.

The Tarifa Branca group is only registered when modalidade_tarifaria == "branca".
On options change the integration reloads (update_listener), which re-evaluates
the condition and adds or removes the entities accordingly.
"""

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..const import (
    CONF_CICLO_QUEBRA,
    CONF_DIA_LEITURA,
    CONF_MODALIDADE_TARIFARIA,
    CONF_TB_FERIADOS_EXTRAS,
    CONF_TB_INTER1_FIM,
    CONF_TB_INTER1_INI,
    CONF_TB_INTER2_FIM,
    CONF_TB_INTER2_INI,
    CONF_TB_PONTA_FIM,
    CONF_TB_PONTA_INI,
    DEFAULT_CICLO,
    DEFAULT_DIA_LEITURA,
    DEFAULT_MODALIDADE,
    DOMAIN,
    MODALIDADE_BRANCA,
)


async def async_setup_config_entities(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Register config-backed sensor entities.

    Always registers: modalidade, ciclo_quebra, dia_leitura.
    Conditionally registers Tarifa Branca group when modalidade == branca.
    """
    entities: list[SensorEntity] = [
        TarifasDeEnergiaBrasilModalidadeSensor(entry),
        TarifasDeEnergiaBrasilCicloQuebraSensor(entry),
        TarifasDeEnergiaBrasilDiaLeituraSensor(entry),
    ]

    if entry.options.get(CONF_MODALIDADE_TARIFARIA, DEFAULT_MODALIDADE) == MODALIDADE_BRANCA:
        entities.extend(_build_tarifa_branca_entities(entry))

    async_add_entities(entities)


def _build_tarifa_branca_entities(entry: ConfigEntry) -> list[SensorEntity]:
    """Cria as entidades do grupo Tarifa Branca."""
    return [
        TarifasDeEnergiaBrasilTBHorarioSensor(
            entry,
            key=CONF_TB_PONTA_INI,
            name="Ponta — Início",
            icon="mdi:clock-start",
        ),
        TarifasDeEnergiaBrasilTBHorarioSensor(
            entry,
            key=CONF_TB_PONTA_FIM,
            name="Ponta — Fim",
            icon="mdi:clock-end",
        ),
        TarifasDeEnergiaBrasilTBHorarioSensor(
            entry,
            key=CONF_TB_INTER1_INI,
            name="Intermediário 1 — Início",
            icon="mdi:clock-start",
        ),
        TarifasDeEnergiaBrasilTBHorarioSensor(
            entry,
            key=CONF_TB_INTER1_FIM,
            name="Intermediário 1 — Fim",
            icon="mdi:clock-end",
        ),
        TarifasDeEnergiaBrasilTBHorarioSensor(
            entry,
            key=CONF_TB_INTER2_INI,
            name="Intermediário 2 — Início",
            icon="mdi:clock-start",
        ),
        TarifasDeEnergiaBrasilTBHorarioSensor(
            entry,
            key=CONF_TB_INTER2_FIM,
            name="Intermediário 2 — Fim",
            icon="mdi:clock-end",
        ),
        TarifasDeEnergiaBrasilTBFeriadosSensor(entry),
    ]


def _device_info(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
    )


# ---------------------------------------------------------------------------
# Entidades de configuração básica
# ---------------------------------------------------------------------------


class TarifasDeEnergiaBrasilModalidadeSensor(SensorEntity):
    """Expõe a modalidade tarifária configurada pelo usuário."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:transmission-tower"

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize."""
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_modalidade_tarifaria"
        self._attr_device_info = _device_info(entry)

    @property
    def name(self) -> str:
        return "Modalidade Tarifária"

    @property
    def native_value(self) -> str:
        return self._entry.options.get(CONF_MODALIDADE_TARIFARIA, DEFAULT_MODALIDADE)

    @property
    def available(self) -> bool:
        return True


class TarifasDeEnergiaBrasilCicloQuebraSensor(SensorEntity):
    """Expõe o ciclo de quebra de cálculo configurado pelo usuário."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:calendar-sync"

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize."""
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_ciclo_quebra"
        self._attr_device_info = _device_info(entry)

    @property
    def name(self) -> str:
        return "Ciclo de Quebra de Cálculo"

    @property
    def native_value(self) -> str:
        return self._entry.options.get(CONF_CICLO_QUEBRA, DEFAULT_CICLO)

    @property
    def available(self) -> bool:
        return True


class TarifasDeEnergiaBrasilDiaLeituraSensor(SensorEntity):
    """Expõe o dia de leitura/reset configurado pelo usuário."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:calendar-today"
    _attr_native_unit_of_measurement = "dia"

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize."""
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_dia_leitura"
        self._attr_device_info = _device_info(entry)

    @property
    def name(self) -> str:
        return "Dia de Leitura/Reset Mensal"

    @property
    def native_value(self) -> int:
        return int(self._entry.options.get(CONF_DIA_LEITURA, DEFAULT_DIA_LEITURA))

    @property
    def available(self) -> bool:
        return True


# ---------------------------------------------------------------------------
# Grupo Tarifa Branca — criado apenas quando modalidade == "branca"
# ---------------------------------------------------------------------------


class TarifasDeEnergiaBrasilTBHorarioSensor(SensorEntity):
    """Expõe um horário da Tarifa Branca (ponta ou intermediário)."""

    _attr_has_entity_name = True
    _attr_entity_registry_enabled_default = True

    def __init__(self, entry: ConfigEntry, key: str, name: str, icon: str) -> None:
        """Initialize."""
        self._entry = entry
        self._key = key
        self._name = name
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = _device_info(entry)
        self._attr_icon = icon

    @property
    def name(self) -> str:
        return f"Tarifa Branca — {self._name}"

    @property
    def native_value(self) -> str | None:
        return self._entry.options.get(self._key)

    @property
    def available(self) -> bool:
        return self._entry.options.get(CONF_MODALIDADE_TARIFARIA) == MODALIDADE_BRANCA


class TarifasDeEnergiaBrasilTBFeriadosSensor(SensorEntity):
    """Expõe os feriados extras configurados para a Tarifa Branca."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:calendar-remove"
    _attr_entity_registry_enabled_default = True

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize."""
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_tb_feriados_extras"
        self._attr_device_info = _device_info(entry)

    @property
    def name(self) -> str:
        return "Tarifa Branca — Feriados Extras"

    @property
    def native_value(self) -> str | None:
        """Retorna os feriados como string (uma data por linha)."""
        value = self._entry.options.get(CONF_TB_FERIADOS_EXTRAS, "")
        return value or None

    @property
    def available(self) -> bool:
        return self._entry.options.get(CONF_MODALIDADE_TARIFARIA) == MODALIDADE_BRANCA
