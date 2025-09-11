"""A integração Tarifas de Energia Brasil."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, CONF_CONCESSIONARIA
from .database import DatabaseManager
from .api import TarifasEnergiaAPI
from .coordinator import TarifasEnergiaCoordinator

_LOGGER = logging.getLogger(__name__)

# Define as plataformas que sua integração usará (neste caso, apenas sensor)
PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configura a integração a partir de uma entrada de configuração (via UI)."""
    # Cria um dicionário central para a integração no Home Assistant
    hass.data.setdefault(DOMAIN, {})

    # 1. Obter a concessionária escolhida pelo usuário durante a configuração
    concessionaria_nome = entry.data[CONF_CONCESSIONARIA]

    # 2. Inicializar o gerenciador do banco de dados
    # O arquivo do banco de dados será salvo na pasta de configuração do HA
    db_path = hass.config.path(f"{DOMAIN}.sqlite")
    db_manager = DatabaseManager(hass, db_path)
    await db_manager.async_setup_database() # Garante que as tabelas existam

    # 3. Inicializar o cliente da API e o Coordenador
    session = async_get_clientsession(hass)
    api_client = TarifasEnergiaAPI(hass, session, db_manager)
    coordinator = TarifasEnergiaCoordinator(hass, api_client, concessionaria_nome)

    # 4. Realizar a primeira busca de dados ao iniciar
    await coordinator.async_config_entry_first_refresh()

    # 5. Armazenar o coordenador para que as plataformas (sensor) possam usá-lo
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # 6. Encaminhar a configuração para as plataformas definidas
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Retorna True se tudo ocorreu bem
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Descarrega uma entrada de configuração (quando o usuário remove a integração)."""
    # Descarrega as plataformas associadas a esta entrada
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # Se o descarregamento foi bem-sucedido, remove os dados da integração
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
