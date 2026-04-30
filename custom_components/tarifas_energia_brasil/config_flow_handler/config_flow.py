"""Main config flow for Tarifas de Energia Brasil."""

from typing import Any

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from ..const import (
    CONF_CONCESSIONARIA,
    CONF_MODALIDADE_TARIFARIA,
    CONF_MODO_IMPOSTOS,
    DOMAIN,
    MODALIDADE_BRANCA,
    MODO_IMPOSTOS_MANUAL,
)
from .options_flow import TarifasDeEnergiaBrasilOptionsFlowHandler
from .schemas.user import get_user_schema
from .validators.user import validate_user_input


class TarifasDeEnergiaBrasilConfigFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Lida com o fluxo de configuração inicial."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize config flow."""
        self._user_data: dict[str, Any] | None = None
        self._options_data: dict[str, Any] = {}
        self._concessionaria_selecionada: str | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Retorna o manipulador de fluxo de opções."""
        return TarifasDeEnergiaBrasilOptionsFlowHandler()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            self._concessionaria_selecionada = user_input[CONF_CONCESSIONARIA]
            await self.async_set_unique_id(self._concessionaria_selecionada)
            self._abort_if_unique_id_configured()
            self._user_data = user_input
            return await self.async_step_options()

        errors, lista_concessionarias = await validate_user_input(self.hass)

        if not lista_concessionarias:
            return self.async_show_form(step_id="user", errors=errors)

        data_schema = get_user_schema(lista_concessionarias)

        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

    async def async_step_options(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Segundo passo na configuração: opções avançadas."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._options_data.update(user_input)
            if user_input.get(CONF_MODALIDADE_TARIFARIA) == MODALIDADE_BRANCA:
                return await self.async_step_tarifa_branca()
            if user_input.get(CONF_MODO_IMPOSTOS) == MODO_IMPOSTOS_MANUAL:
                return await self.async_step_manual_taxes()
            return self.async_create_entry(
                title=self._concessionaria_selecionada,
                data=self._user_data,
                options=self._options_data,
            )

        from ..utils.scrapers import has_scraper
        from .schemas.options import get_options_schema

        suporta_automatico = has_scraper(self._concessionaria_selecionada)
        data_schema = get_options_schema({}, suporta_automatico)

        return self.async_show_form(step_id="options", data_schema=data_schema, errors=errors)

    async def async_step_tarifa_branca(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Passo de configuração dos horários da Tarifa Branca."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._options_data.update(user_input)
            if self._options_data.get(CONF_MODO_IMPOSTOS) == MODO_IMPOSTOS_MANUAL:
                return await self.async_step_manual_taxes()
            return self.async_create_entry(
                title=self._concessionaria_selecionada,
                data=self._user_data,
                options=self._options_data,
            )

        from .schemas.tarifa_branca import get_tarifa_branca_schema

        data_schema = get_tarifa_branca_schema({})
        return self.async_show_form(step_id="tarifa_branca", data_schema=data_schema, errors=errors)

    async def async_step_manual_taxes(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Passo de configuração dos impostos manuais."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._options_data.update(user_input)
            return self.async_create_entry(
                title=self._concessionaria_selecionada,
                data=self._user_data,
                options=self._options_data,
            )

        from .schemas.options import get_manual_taxes_schema

        data_schema = get_manual_taxes_schema({})
        return self.async_show_form(step_id="manual_taxes", data_schema=data_schema, errors=errors)

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        """Perform reauth upon an API authentication error."""
        # Scaffold para fluxo de reautenticação futuro
        return self.async_abort(reason="not_supported")

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Reconfigure the integration."""
        # Scaffold para fluxo de reconfiguração futuro
        return self.async_abort(reason="not_supported")
