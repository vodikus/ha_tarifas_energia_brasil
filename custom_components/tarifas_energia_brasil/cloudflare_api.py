"""Cliente HTTP para a API Cloudflare Worker de tarifas de energia."""
import logging

from homeassistant.core import HomeAssistant
from aiohttp import ClientSession, ClientError

from .const import CLOUDFLARE_BASE_URL

_LOGGER = logging.getLogger(__name__)


class CloudflareAPI:
    """Classe responsável pelas chamadas HTTP ao serviço Cloudflare Worker."""

    def __init__(self, hass: HomeAssistant, session: ClientSession):
        self._hass = hass
        self._session = session

    async def async_fetch_concessionarias(self) -> list[str]:
        """Busca a lista de concessionárias disponíveis."""
        url = f"{CLOUDFLARE_BASE_URL}/tarifas/concessionarias"
        try:
            async with self._session.get(url, timeout=30) as resp:
                resp.raise_for_status()
                data = await resp.json()
                if not isinstance(data, list):
                    raise ValueError(f"Resposta inesperada: {data}")
                return data
        except ClientError as err:
            _LOGGER.error("Erro ao buscar concessionárias: %s", err)
            raise
        except Exception as err:
            _LOGGER.error("Erro inesperado ao buscar concessionárias: %s", err)
            raise

    async def async_fetch_tarifas(self, concessionaria: str, nocache: bool = False) -> dict:
        """Busca tarifa e bandeira vigentes para a concessionária informada.

        Args:
            concessionaria: Nome da concessionária (ex: 'CELESC').
            nocache: Se True, envia nocache=true na query string para
                     forçar o Cloudflare Worker a ignorar o cache e
                     buscar dados frescos da fonte.

        Returns:
            Dict com estrutura: { concessionaria, bandeira_tarifaria, tarifa }
        """
        url = f"{CLOUDFLARE_BASE_URL}/tarifas/atual"
        params: dict[str, str] = {"concessionaria": concessionaria}
        if nocache:
            params["nocache"] = "true"

        try:
            async with self._session.get(url, params=params, timeout=30) as resp:
                resp.raise_for_status()
                data = await resp.json()
                if not isinstance(data, dict) or "tarifa" not in data:
                    raise ValueError(f"Resposta inesperada da API: {data}")
                return data
        except ClientError as err:
            _LOGGER.error("Erro ao buscar tarifas de '%s': %s", concessionaria, err)
            raise
        except Exception as err:
            _LOGGER.error("Erro inesperado ao buscar tarifas: %s", err)
            raise
