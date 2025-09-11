"""API Client para a integração Tarifas de Energia Brasil."""
import logging
import json
import aiohttp
from datetime import date

from .database import DatabaseManager

_LOGGER = logging.getLogger(__name__)

# URL base da API da ANEEL para consultas SQL
URL_SQL_API = "https://dadosabertos.aneel.gov.br/api/3/action/datastore_search_sql"
# URL base da API da ANEEL para buscas normais
URL_SEARCH_API = "https://dadosabertos.aneel.gov.br/api/3/action/datastore_search"

# IDs dos recursos (datasets) na ANEEL
RESOURCE_ID_TARIFAS = "fcf2906c-7c32-4b9b-a637-054e7a5234f4"
RESOURCE_ID_BANDEIRAS = "0591b8f6-fe54-437b-b72b-1aa2efd46e42"


class TarifasEnergiaAPI:
    """Cliente para buscar dados de tarifas e gerenciar o banco de dados."""

    def __init__(self, hass, session: aiohttp.ClientSession, db_manager: DatabaseManager):
        """Inicializa o cliente da API."""
        self._hass = hass
        self._session = session
        self._db = db_manager

    async def _async_get_valores_bandeiras(self, competencia: date) -> dict[str, float] | None:
        """Busca os valores de todas as bandeiras tarifárias para um determinado mês."""
        primeiro_dia_mes = competencia.strftime("%Y-%m-01")
        
        params = {
            "resource_id": RESOURCE_ID_BANDEIRAS,
            "filters": json.dumps({"DatCompetencia": primeiro_dia_mes}),
            "limit": 1
        }
        
        _LOGGER.info(f"Buscando valores das bandeiras tarifárias para {primeiro_dia_mes}")

        try:
            async with self._session.get(URL_SEARCH_API, params=params) as response:
                response.raise_for_status()
                data = await response.json()

                if data.get("success"):
                    records = data.get("result", {}).get("records", [])
                    if records:
                        record = records[0]
                        valores = {
                            "Bandeira Verde": 0.0,
                            "Bandeira Amarela": float(record.get("VlrBandeiraAmarela", 0.0)),
                            "Bandeira Vermelha Patamar 1": float(record.get("VlrBandeiraVermelhaPatamar1", 0.0)),
                            "Bandeira Vermelha Patamar 2": float(record.get("VlrBandeiraVermelhaPatamar2", 0.0)),
                        }
                        _LOGGER.info(f"Valores das bandeiras encontrados: {valores}")
                        return valores
                    
                    _LOGGER.warning(f"Nenhum valor de bandeira encontrado para {primeiro_dia_mes}.")
                    return None
                
                _LOGGER.error(f"A API de bandeiras da ANEEL retornou um erro: {data.get('error')}")
                return None

        except aiohttp.ClientError as err:
            _LOGGER.error(f"Erro ao acessar a API de bandeiras tarifárias: {err}")
            return None
        except (ValueError, TypeError) as err:
            _LOGGER.error(f"Erro ao processar os valores das bandeiras: {err}")
            return None

    async def async_get_bandeira_vigente(self, competencia: date) -> str | None:
        """Busca a bandeira tarifária vigente para um determinado mês usando SQL."""
        mes_ano = competencia.strftime("%Y-%m")
        sql_query = f'SELECT "NomBandeiraAcionada" from "{RESOURCE_ID_BANDEIRAS}" WHERE "DatCompetencia" LIKE \'{mes_ano}%\' LIMIT 1'
        
        params = {"sql": sql_query}
        
        _LOGGER.info(f"Buscando bandeira tarifária para {mes_ano} via SQL.")
        _LOGGER.debug(f"Executando SQL na API da ANEEL: {sql_query}")

        try:
            async with self._session.get(URL_SQL_API, params=params) as response:
                response.raise_for_status()
                data = await response.json()

                if data.get("success"):
                    records = data.get("result", {}).get("records", [])
                    if records:
                        bandeira_acionada = records[0].get("NomBandeiraAcionada")
                        _LOGGER.info(f"Bandeira acionada encontrada para {mes_ano}: {bandeira_acionada}")

                        # Mapeamento dos valores da API para os nomes completos usados no sistema
                        mapa_bandeiras = {
                            "Verde": "Bandeira Verde",
                            "Amarela": "Bandeira Amarela",
                            "Vermelha P1": "Bandeira Vermelha Patamar 1",
                            "Vermelha P2": "Bandeira Vermelha Patamar 2",
                        }
                        
                        bandeira_mapeada = mapa_bandeiras.get(bandeira_acionada, bandeira_acionada)
                        if bandeira_acionada not in mapa_bandeiras:
                             _LOGGER.warning(f"Bandeira '{bandeira_acionada}' não possui mapeamento. Usando valor original.")
                        
                        return bandeira_mapeada
                    
                    _LOGGER.warning(f"Nenhuma bandeira tarifária encontrada para {mes_ano}.")
                    return None
                
                _LOGGER.error(f"A API da ANEEL para bandeiras (SQL) retornou um erro: {data.get('error')}")
                return None

        except aiohttp.ClientError as err:
            _LOGGER.error(f"Erro ao acessar a API SQL de bandeiras tarifárias: {err}")
            return None
        except Exception as err:
            _LOGGER.error(f"Erro inesperado ao processar a bandeira tarifária via SQL: {err}")
            return None

    async def async_fetch_concessionarias(self) -> bool:
        """
        Busca a lista de concessionárias via API SQL da ANEEL e atualiza o banco de dados.
        Retorna True se bem-sucedido.
        """
        _LOGGER.info("Iniciando a busca da lista de concessionárias via API SQL da ANEEL.")
        sql_query = f'SELECT "SigAgente" from "{RESOURCE_ID_TARIFAS}" group by "SigAgente"'
        params = {"sql": sql_query}

        try:
            async with self._session.get(URL_SQL_API, params=params) as response:
                response.raise_for_status()
                data = await response.json()

                if not data.get("success"):
                    _LOGGER.error(f"A API de concessionárias da ANEEL retornou um erro: {data.get('error')}")
                    return False

                records = data.get("result", {}).get("records", [])
                if not records:
                    _LOGGER.warning("Nenhuma concessionária encontrada na resposta da API.")
                    return False
                
                nomes_concessionarias = {record["SigAgente"] for record in records if "SigAgente" in record}

                if not nomes_concessionarias:
                    _LOGGER.warning("Os registros da API não continham a chave 'SigAgente'.")
                    return False

                await self._db.async_update_concessionarias(nomes_concessionarias)
                return True

        except aiohttp.ClientError as err:
            _LOGGER.error(f"Erro ao acessar a API da ANEEL: {err}")
            return False
        except (KeyError, json.JSONDecodeError) as err:
            _LOGGER.error(f"Erro ao processar o JSON da lista de concessionárias: {err}")
            return False
        except Exception as err:
            _LOGGER.error(f"Erro inesperado ao buscar a lista de concessionárias: {err}")
            return False

    async def async_fetch_and_update_data(self, concessionaria_nome: str):
        """
        Busca a tarifa base usando uma query SQL e os valores das bandeiras, 
        calcula as tarifas finais e atualiza o banco de dados.
        """
        hoje = date.today()
        _LOGGER.info(f"Iniciando atualização de tarifas para '{concessionaria_nome}' via SQL em {hoje}.")

        valores_bandeiras = await self._async_get_valores_bandeiras(hoje)
        if valores_bandeiras is None:
            _LOGGER.error("Não foi possível obter os valores das bandeiras. Abortando atualização.")
            return None

        tarifa_base = None
        
        # Monta a query SQL com os filtros especificados
        sql_query = (
            f'SELECT "VlrTUSD", "VlrTE" FROM "{RESOURCE_ID_TARIFAS}" '
            f'WHERE "SigAgente" = \'{concessionaria_nome}\' '
            f'AND "DscBaseTarifaria" = \'Tarifa de Aplicação\' '
            f'AND "DscSubGrupo" = \'B1\' '
            f'AND "DscClasse" = \'Residencial\' '
            f'AND "DscModalidadeTarifaria" = \'Convencional\' '
            f'AND "DscSubClasse" = \'Residencial\' '
            f'AND "DscDetalhe" = \'Não se aplica\' '
            f'AND "DatFimVigencia" > \'{hoje.strftime("%Y-%m-%d")}\' '
            'LIMIT 1'
        )
        
        params = {"sql": sql_query}
        
        try:
            _LOGGER.debug(f"Executando SQL na API da ANEEL: {sql_query}")
            async with self._session.get(URL_SQL_API, params=params) as response:
                response.raise_for_status()
                data = await response.json()

                if not data.get("success"):
                    _LOGGER.error(f"A API de tarifas da ANEEL retornou um erro: {data.get('error')}")
                    return None

                records = data.get("result", {}).get("records", [])
                if not records:
                    _LOGGER.error(f"Nenhuma tarifa base vigente encontrada para '{concessionaria_nome}' com os filtros aplicados via SQL.")
                    return None

                record = records[0]
                
                vlr_tusd_raw = record.get("VlrTUSD", "0")
                vlr_te_raw = record.get("VlrTE", "0")

                vlr_tusd = float(str(vlr_tusd_raw).replace(",", "."))
                vlr_te = float(str(vlr_te_raw).replace(",", "."))

                tarifa_base = vlr_tusd + vlr_te
                _LOGGER.info(f"Tarifa base encontrada para {concessionaria_nome}: {tarifa_base:.4f}")

        except aiohttp.ClientError as err:
            _LOGGER.error(f"Erro ao acessar a API SQL de tarifas: {err}")
            return None
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as err:
            _LOGGER.error(f"Erro ao processar o JSON da tarifa: {err}")
            return None
        
        if tarifa_base is None:
            _LOGGER.error(f"Falha ao determinar a tarifa base para '{concessionaria_nome}'.")
            return None

        # Calcula os valores finais e atualiza o banco de dados
        tarifas_finais = {
            "Bandeira Verde": tarifa_base + valores_bandeiras["Bandeira Verde"],
            "Bandeira Amarela": tarifa_base + valores_bandeiras["Bandeira Amarela"],
            "Bandeira Vermelha Patamar 1": tarifa_base + valores_bandeiras["Bandeira Vermelha Patamar 1"],
            "Bandeira Vermelha Patamar 2": tarifa_base + valores_bandeiras["Bandeira Vermelha Patamar 2"],
        }
        
        await self._db.async_update_tarifas(concessionaria_nome, tarifas_finais)
        _LOGGER.info(f"Tarifas finais para {concessionaria_nome} atualizadas com sucesso.")

        return await self._db.async_get_tarifas(concessionaria_nome)

