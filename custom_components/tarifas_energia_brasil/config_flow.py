"""Config flow para a integração Tarifas de Energia Brasil."""
import logging
import voluptuous as vol
from typing import Any

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, CONF_CONCESSIONARIA
from .api import TarifasEnergiaAPI
from .database import DatabaseManager

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
            # O usuário submeteu o formulário. Validar e criar a entrada.
            concessionaria_selecionada = user_input[CONF_CONCESSIONARIA]

            # Define um ID único para evitar duplicatas
            await self.async_set_unique_id(concessionaria_selecionada)
            self._abort_if_unique_id_configured()

            # Cria a entrada de configuração e finaliza o fluxo
            return self.async_create_entry(
                title=concessionaria_selecionada, data=user_input
            )

        # --- Se user_input é None, mostra o formulário pela primeira vez ---
        
        # Inicializa as dependências para buscar a lista de concessionárias
        db_path = self.hass.config.path(f"{DOMAIN}.sqlite")
        db_manager = DatabaseManager(self.hass, db_path)
        session = async_get_clientsession(self.hass)
        api_client = TarifasEnergiaAPI(self.hass, session, db_manager)
        
        # Garante que as tabelas do banco de dados existam
        await db_manager.async_setup_database()

        # Busca a lista mais recente de concessionárias do site da ANEEL
        success = await api_client.async_fetch_concessionarias()
        if not success:
            errors["base"] = "cannot_connect"
            # Mostra um formulário com erro se não conseguir conectar
            return self.async_show_form(step_id="user", errors=errors)

        # Obtém a lista completa do nosso banco de dados local
        lista_concessionarias = await db_manager.async_get_all_concessionarias()

        if not lista_concessionarias:
            errors["base"] = "no_concessionarias"
            # Mostra um formulário com erro se a lista estiver vazia
            return self.async_show_form(step_id="user", errors=errors)

        # Cria o esquema do formulário com a lista dinâmica
        data_schema = vol.Schema(
            {
                vol.Required(CONF_CONCESSIONARIA): vol.In(sorted(lista_concessionarias))
            }
        )

        # Mostra o formulário para o usuário
        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )
