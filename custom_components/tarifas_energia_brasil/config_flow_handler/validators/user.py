"""Validação para o Config Flow do usuário."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ...api import TarifasDeEnergiaBrasilAPI
from ...const import DOMAIN
from ...utils.database import DatabaseManager


async def validate_user_input(hass: HomeAssistant) -> tuple[dict[str, str], list[str]]:
    """Valida a conexão com a API e o banco de dados, e retorna a lista de concessionárias disponíveis."""
    errors = {}
    db_path = hass.config.path(f"{DOMAIN}.sqlite")
    db_manager = DatabaseManager(hass, db_path)
    session = async_get_clientsession(hass)
    api_client = TarifasDeEnergiaBrasilAPI(hass, session, db_manager)

    await db_manager.async_setup_database()

    success = await api_client.async_fetch_concessionarias()
    if not success:
        errors["base"] = "cannot_connect"

    lista_concessionarias = await db_manager.async_get_all_concessionarias()
    if not lista_concessionarias:
        errors["base"] = "no_concessionarias"
        return errors, []

    return errors, lista_concessionarias
