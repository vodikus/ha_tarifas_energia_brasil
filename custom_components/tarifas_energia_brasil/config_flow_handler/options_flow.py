"""Options Flow handler for Tarifas de Energia Brasil."""

from typing import Any

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from ..const import (
    CONF_CONCESSIONARIA,
    CONF_MODALIDADE_TARIFARIA,
    CONF_MODO_IMPOSTOS,
    MODALIDADE_BRANCA,
    MODO_IMPOSTOS_MANUAL,
)
from ..utils.scrapers import has_scraper
from .schemas.options import get_manual_taxes_schema, get_options_schema
from .schemas.tarifa_branca import get_tarifa_branca_schema


class TarifasDeEnergiaBrasilOptionsFlowHandler(config_entries.OptionsFlow):
    """Manipula o fluxo de opções (Opções Avançadas)."""

    def __init__(self) -> None:
        """Initialize options flow."""
        self._options_data: dict[str, Any] = {}

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Ponto de entrada do Options Flow."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._options_data.update(user_input)
            if user_input.get(CONF_MODALIDADE_TARIFARIA) == MODALIDADE_BRANCA:
                return await self.async_step_tarifa_branca()
            if user_input.get(CONF_MODO_IMPOSTOS) == MODO_IMPOSTOS_MANUAL:
                return await self.async_step_manual_taxes()
            return self.async_create_entry(title="", data=self._options_data)

        concessionaria = self.config_entry.data.get(CONF_CONCESSIONARIA)
        suporta_automatico = has_scraper(concessionaria)
        data_schema = get_options_schema(self.config_entry.options, suporta_automatico)

        return self.async_show_form(step_id="init", data_schema=data_schema, errors=errors)

    async def async_step_tarifa_branca(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Configuração dos horários da Tarifa Branca."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._options_data.update(user_input)
            if self._options_data.get(CONF_MODO_IMPOSTOS) == MODO_IMPOSTOS_MANUAL:
                return await self.async_step_manual_taxes()
            return self.async_create_entry(title="", data=self._options_data)

        data_schema = get_tarifa_branca_schema(self.config_entry.options)
        return self.async_show_form(step_id="tarifa_branca", data_schema=data_schema, errors=errors)

    async def async_step_manual_taxes(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Configuração manual de impostos."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._options_data.update(user_input)
            return self.async_create_entry(title="", data=self._options_data)

        data_schema = get_manual_taxes_schema(self.config_entry.options)
        return self.async_show_form(step_id="manual_taxes", data_schema=data_schema, errors=errors)
