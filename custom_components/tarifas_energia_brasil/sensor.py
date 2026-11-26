"""Define as entidades de sensor para a integração Tarifas de Energia Brasil."""

import logging
from datetime import date

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    CONF_CONCESSIONARIA,
    STATUS_CACHE,
    STATUS_ONLINE,
    STATUS_SEM_DADOS,
    DATA_CURRENT,
    DATA_EXPIRED,
    DATA_FUTURE,
    DATA_FLAG_STALE,
    DATA_INCOMPLETE,
    DATA_UNAVAILABLE,
)
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
        StatusAtualizacaoSensor(coordinator, entry),
        UltimaConsultaSensor(coordinator, entry),
        UltimaConsultaSucessoSensor(coordinator, entry),
        AtualidadeDadosSensor(coordinator, entry),
    ]

    async_add_entities(entities)


class TarifasEnergiaBaseSensor(
    CoordinatorEntity[TarifasEnergiaCoordinator], SensorEntity
):
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
    # Sem device_class: MONETARY exige código ISO-4217 (ex.: BRL), e "R$/kWh" é taxa por energia.
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
        # Texto cru da API (sem offset comprovado); não é data/hora com fuso.
        if self.coordinator.data:
            return self.coordinator.data.get("timestamp")
        return None


class DiagnosticoBaseSensor(TarifasEnergiaBaseSensor):
    """Diagnósticos continuam disponíveis mesmo sem dado de tarifa (mostram sem_dados)."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def available(self) -> bool:
        return True


class StatusAtualizacaoSensor(DiagnosticoBaseSensor):
    """Estado da última atualização: online, cache ou sem dados válidos."""

    _attr_name = "Status da Atualização"
    _attr_translation_key = "status_atualizacao"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [STATUS_ONLINE, STATUS_CACHE, STATUS_SEM_DADOS]
    _attr_icon = "mdi:cloud-check"

    def __init__(self, coordinator: TarifasEnergiaCoordinator, entry: ConfigEntry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{self.entry.entry_id}_status_atualizacao"

    @property
    def native_value(self) -> str:
        # HA mantém o dado anterior quando a última tentativa falha: nesse caso não há dado atual.
        data = self.coordinator.data
        if not data or not self.coordinator.last_update_success:
            return STATUS_SEM_DADOS
        return data.get("data_status", STATUS_SEM_DADOS)

    @property
    def extra_state_attributes(self) -> dict | None:
        data = self.coordinator.data
        if not data:
            return {"vigencia_expirada": None}
        fim = data.get("dat_fim_vigencia")
        expirada = None
        if isinstance(fim, str):
            try:
                expirada = date.fromisoformat(fim[:10]) < dt_util.now().date()
            except ValueError:
                expirada = None
        return {
            "vigencia_expirada": expirada,
            "ultima_consulta_erro": self.coordinator.last_error,
        }


class UltimaConsultaSensor(DiagnosticoBaseSensor):
    """Horário local da última tentativa de consulta à API."""

    _attr_name = "Última Consulta"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:clock-check-outline"

    def __init__(self, coordinator: TarifasEnergiaCoordinator, entry: ConfigEntry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{self.entry.entry_id}_ultima_consulta"

    @property
    def native_value(self):
        return self.coordinator.last_attempt


class UltimaConsultaSucessoSensor(DiagnosticoBaseSensor):
    """Horário local da última consulta bem-sucedida (nunca preenchido pelo cache)."""

    _attr_name = "Última Consulta com Sucesso"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:clock-check"

    def __init__(self, coordinator: TarifasEnergiaCoordinator, entry: ConfigEntry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{self.entry.entry_id}_ultima_consulta_sucesso"

    @property
    def native_value(self):
        return self.coordinator.last_success


class AtualidadeDadosSensor(DiagnosticoBaseSensor):
    """Separa a atualidade do conteúdo da conectividade com o intermediário."""

    _attr_name = "Atualidade dos Dados"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_translation_key = "atualidade_dados"
    _attr_options = [
        DATA_CURRENT,
        DATA_EXPIRED,
        DATA_FUTURE,
        DATA_FLAG_STALE,
        DATA_INCOMPLETE,
        DATA_UNAVAILABLE,
    ]
    _attr_icon = "mdi:calendar-check"

    def __init__(self, coordinator: TarifasEnergiaCoordinator, entry: ConfigEntry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{self.entry.entry_id}_atualidade_dados"

    @property
    def native_value(self) -> str:
        data = self.coordinator.data
        if not data or not self.coordinator.last_update_success:
            return DATA_UNAVAILABLE
        today = dt_util.now().date()
        try:
            inicio = date.fromisoformat(data["dat_inicio_vigencia"])
            fim = date.fromisoformat(data["dat_fim_vigencia"])
        except (KeyError, TypeError, ValueError):
            return DATA_INCOMPLETE
        if fim < today:
            return DATA_EXPIRED
        if inicio > today:
            return DATA_FUTURE
        comp = data.get("dat_competencia_bandeira")
        if not isinstance(comp, date):
            return DATA_INCOMPLETE
        if (comp.year, comp.month) != (today.year, today.month):
            return DATA_FLAG_STALE
        return DATA_CURRENT

    @property
    def extra_state_attributes(self):
        return {
            "fonte_consulta": "servico_intermediario",
            "modo_atualizacao": self.coordinator.polling_mode,
            "intervalo_horas": self.coordinator.update_interval.total_seconds() / 3600,
        }
