"""DataUpdateCoordinator para a integração Tarifas de Energia Brasil."""
import logging
from datetime import timedelta, date

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.core import HomeAssistant


from .api import TarifasEnergiaAPI
from .const import DOMAIN
from .utils import save_last_data, load_last_data

_LOGGER = logging.getLogger(__name__)


class TarifasEnergiaCoordinator(DataUpdateCoordinator):
    from .utils import save_last_data, load_last_data
    """Coordenador para buscar e gerenciar os dados de tarifas."""

    def __init__(self, hass: HomeAssistant, api: TarifasEnergiaAPI, concessionaria: str):
        """Inicializa o coordenador."""
        self.api = api
        self.concessionaria = concessionaria
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(days=1),  # Atualiza uma vez por dia
        )

    async def _async_update_data(self) -> dict:
        """
        Busca os dados mais recentes da API.

        Esta função é chamada automaticamente pelo Home Assistant no intervalo definido.
        """
        try:
            # 1. Busca os valores calculados para todas as bandeiras
            tarifas = await self.api.async_fetch_and_update_data(self.concessionaria)
            if not tarifas:
                await save_last_data(None, None, "offline")
                raise UpdateFailed("Não foi possível obter os valores das tarifas.")

            # 2. Busca o nome da bandeira vigente para o mês corrente
            bandeira_vigente = await self.api.async_get_bandeira_vigente(date.today())
            if not bandeira_vigente:
                await save_last_data(None, None, "offline")
                raise UpdateFailed("Não foi possível obter a bandeira tarifária vigente.")

            _LOGGER.info(
                f"Atualização bem-sucedida. Bandeira vigente: '{bandeira_vigente}'."
            )

            # Salva os dados e status da API
            try:
                # tarifa vigente é a tarifa da bandeira vigente, se possível
                tarifa_vigente = None
                if tarifas and bandeira_vigente in tarifas:
                    tarifa_vigente = tarifas[bandeira_vigente] / 1000
                await save_last_data(tarifa_vigente, bandeira_vigente, "online")
            except Exception as e:
                _LOGGER.error(f"Erro ao salvar last_data.json: {e}")

            return {
                "tarifas": tarifas,
                "bandeira_vigente": bandeira_vigente,
                "api_status": "online",
                "timestamp": (await load_last_data() or {}).get("timestamp"),
            }

        except Exception as err:
            _LOGGER.error(f"Erro inesperado durante a atualização: {err}")
            # Tenta retornar o último dado salvo, se existir
            last_data = await load_last_data()
            if last_data:
                return {
                    "tarifas": None,
                    "bandeira_vigente": last_data.get("bandeira_vigente"),
                    "tarifa_vigente": last_data.get("tarifa_vigente"),
                    "api_status": last_data.get("api_status", "offline"),
                    "timestamp": last_data.get("timestamp"),
                }
            raise UpdateFailed(f"Erro ao buscar dados: {err}")

