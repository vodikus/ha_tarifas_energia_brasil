"""DataUpdateCoordinator para a integração Tarifas de Energia Brasil."""
import logging
from datetime import timedelta

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
            # Busca, calcula e persiste a tarifa da bandeira vigente
            resultado = await self.api.async_fetch_and_update_data(self.concessionaria)
            if not resultado:
                raise UpdateFailed("Não foi possível obter os valores das tarifas.")

            dat_competencia_bandeira = await self.api.async_get_latest_bandeira_competencia()

            _LOGGER.info(
                f"Atualização bem-sucedida. Bandeira vigente: '{resultado['bandeira_vigente']}'."
            )

            return {
                "bandeira_vigente": resultado["bandeira_vigente"],
                "tarifa_vigente": resultado["tarifa_vigente"],
                "dat_competencia_bandeira": dat_competencia_bandeira,
                "dat_competencia_tarifa": resultado.get("dat_competencia"),
                "api_status": "online",
                "timestamp": resultado.get("timestamp"),
            }

        except Exception as err:
            _LOGGER.error(f"Erro inesperado durante a atualização: {err}")
            # Tenta retornar o último dado salvo no banco, se existir
            last_data = await self.api.async_get_latest_tarifa_snapshot(self.concessionaria)
            if last_data:
                dat_competencia_bandeira = await self.api.async_get_latest_bandeira_competencia()
                return {
                    "bandeira_vigente": last_data.get("bandeira_vigente"),
                    "tarifa_vigente": last_data.get("tarifa_vigente"),
                    "dat_competencia_bandeira": dat_competencia_bandeira,
                    "dat_competencia_tarifa": last_data.get("dat_competencia"),
                    "api_status": "offline",
                    "timestamp": last_data.get("timestamp"),
                }
            raise UpdateFailed(f"Erro ao buscar dados: {err}")

