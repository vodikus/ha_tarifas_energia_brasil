"""DataUpdateCoordinator para a integração Tarifas de Energia Brasil."""
import logging
from datetime import timedelta, date

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.core import HomeAssistant

from .api import TarifasEnergiaAPI
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class TarifasEnergiaCoordinator(DataUpdateCoordinator):
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
                raise UpdateFailed("Não foi possível obter os valores das tarifas.")

            # 2. Busca o nome da bandeira vigente para o mês corrente
            bandeira_vigente = await self.api.async_get_bandeira_vigente(date.today())
            if not bandeira_vigente:
                raise UpdateFailed("Não foi possível obter a bandeira tarifária vigente.")

            _LOGGER.info(
                f"Atualização bem-sucedida. Bandeira vigente: '{bandeira_vigente}'."
            )

            # 3. Retorna um dicionário com todos os dados necessários para os sensores
            return {
                "tarifas": tarifas,
                "bandeira_vigente": bandeira_vigente,
            }

        except Exception as err:
            _LOGGER.error(f"Erro inesperado durante a atualização: {err}")
            raise UpdateFailed(f"Erro ao buscar dados: {err}")

