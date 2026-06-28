"""Config flow para a integração Tarifas de Energia Brasil."""
import logging
import voluptuous as vol
from typing import Any

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, CONF_CONCESSIONARIA
from .cloudflare_api import CloudflareAPI

_LOGGER = logging.getLogger(__name__)


class TarifasEnergiaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Lida com o fluxo de configuração para a integração."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Lida com o passo inicial do fluxo, iniciado pelo usuário."""
        errors: dict[str, str] = {}

        if user_input is not None:
            concessionaria_selecionada = user_input[CONF_CONCESSIONARIA]
            await self.async_set_unique_id(concessionaria_selecionada)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=concessionaria_selecionada, data=user_input)

        session = async_get_clientsession(self.hass)
        api = CloudflareAPI(self.hass, session)

        try:
            lista_concessionarias = await api.async_fetch_concessionarias()
        except Exception:
            errors["base"] = "cannot_connect"
            return self.async_show_form(step_id="user", errors=errors)

        if not lista_concessionarias:
            errors["base"] = "no_concessionarias"
            return self.async_show_form(step_id="user", errors=errors)

        data_schema = vol.Schema(
            {vol.Required(CONF_CONCESSIONARIA): vol.In(sorted(lista_concessionarias))}
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )
