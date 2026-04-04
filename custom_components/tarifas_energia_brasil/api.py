"""API Client para a integração Tarifas de Energia Brasil."""
import logging
import json
import csv
import aiohttp
from datetime import date, datetime

from .database import DatabaseManager


_LOGGER = logging.getLogger(__name__)

# URL base da API da ANEEL para consultas SQL
URL_SQL_API = "https://dadosabertos.aneel.gov.br/api/3/action/datastore_search_sql"
URL_BANDEIRAS_CSV = "https://dadosabertos.aneel.gov.br/dataset/7f43a020-6dc5-44b8-80b4-d97eaa94436c/resource/0591b8f6-fe54-437b-b72b-1aa2efd46e42/download/bandeira-tarifaria-acionamento.csv"

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

    @staticmethod
    def _parse_float_br(valor: str) -> float:
        """Converte valores no formato brasileiro para float."""
        valor_normalizado = valor.strip().replace(".", "").replace(",", ".")
        if valor_normalizado.startswith("."):
            valor_normalizado = f"0{valor_normalizado}"
        if not valor_normalizado:
            return 0.0
        return float(valor_normalizado)

    async def async_preload_latest_bandeira_csv(self) -> bool:
        """
        Faz pre-load da última linha do CSV de bandeiras.

        Insere no banco apenas se a competência da linha for mais recente
        do que a última já registrada.
        """
        _LOGGER.info("Iniciando pre-load do CSV de bandeiras tarifárias.")

        try:
            async with self._session.get(URL_BANDEIRAS_CSV) as response:
                response.raise_for_status()
                csv_bytes = await response.read()

            # O arquivo da ANEEL pode variar de encoding conforme publicação.
            # Tentamos UTF-8 primeiro e, em seguida, encodings comuns em CSVs legados.
            csv_text = None
            encodings_para_tentar = [
                (response.charset or "").strip(),
                "utf-8-sig",
                "utf-8",
                "cp1252",
                "latin-1",
            ]
            for encoding in encodings_para_tentar:
                if not encoding:
                    continue
                try:
                    csv_text = csv_bytes.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue

            if csv_text is None:
                _LOGGER.warning("Não foi possível decodificar o CSV de bandeiras com os encodings suportados.")
                return False

            linhas = [
                row
                for row in csv.reader(csv_text.splitlines(), delimiter=";")
                if len(row) >= 4 and row[1].strip()
            ]
            if not linhas:
                _LOGGER.warning("CSV de bandeiras retornou sem linhas válidas.")
                return False

            ultima_linha = linhas[-1]
            data_geracao = datetime.strptime(ultima_linha[0].strip(), "%Y-%m-%d").date()
            data_competencia = datetime.strptime(ultima_linha[1].strip(), "%Y-%m-%d").date()
            nome_bandeira = ultima_linha[2].strip()
            valor_adicional = self._parse_float_br(ultima_linha[3])

            latest = await self._db.async_get_latest_bandeira_competencia()
            if latest is not None and data_competencia <= latest:
                _LOGGER.info(
                    "Pre-load ignorado: competência %s já está atualizada (última: %s).",
                    data_competencia,
                    latest,
                )
                return False

            inserted = await self._db.async_insert_bandeira_csv_row_if_newer(
                data_geracao,
                data_competencia,
                nome_bandeira,
                valor_adicional,
            )
            if inserted:
                _LOGGER.info(
                    "Pre-load concluído: competência %s inserida no banco.",
                    data_competencia,
                )
            return inserted

        except aiohttp.ClientError as err:
            _LOGGER.warning("Falha ao baixar o CSV de bandeiras: %s", err)
            return False
        except (ValueError, TypeError) as err:
            _LOGGER.warning("Falha ao processar última linha do CSV de bandeiras: %s", err)
            return False

    async def async_get_latest_tarifa_snapshot(self, concessionaria_nome: str) -> dict | None:
        """Retorna a última leitura persistida de tarifa para a concessionária."""
        return await self._db.async_get_latest_tarifa_snapshot(concessionaria_nome)

    async def async_get_latest_bandeira_competencia(self) -> date | None:
        """Retorna a data de competência mais recente da tabela de bandeiras tarifárias."""
        return await self._db.async_get_latest_bandeira_competencia()

    async def async_get_bandeira_vigente(self, competencia: date) -> tuple[str, float, date] | None:
        """Busca a bandeira tarifária vigente, seu valor adicional e data de competência."""
        hoje = competencia.strftime("%Y-%m-%d")
        sql_query = (
            f'SELECT "NomBandeiraAcionada", "VlrAdicionalBandeira", "DatCompetencia" FROM "{RESOURCE_ID_BANDEIRAS}" '
            f'WHERE "DatCompetencia" <= \'{hoje}\' '
            f'ORDER BY "DatCompetencia" DESC LIMIT 1'
        )
        params = {"sql": sql_query}

        _LOGGER.info(f"Buscando bandeira tarifária vigente para {hoje} via SQL.")

        try:
            async with self._session.get(URL_SQL_API, params=params) as response:
                response.raise_for_status()
                data = await response.json()

                if data.get("success"):
                    records = data.get("result", {}).get("records", [])
                    if records:
                        record = records[0]
                        bandeira_acionada = record.get("NomBandeiraAcionada")
                        valor_adicional = self._parse_float_br(
                            str(record.get("VlrAdicionalBandeira", "0"))
                        )
                        dat_competencia = datetime.strptime(
                            str(record.get("DatCompetencia", ""))[:10], "%Y-%m-%d"
                        ).date()

                        mapa_bandeiras = {
                            "Verde": "Bandeira Verde",
                            "Amarela": "Bandeira Amarela",
                            "Vermelha P1": "Bandeira Vermelha Patamar 1",
                            "Vermelha P2": "Bandeira Vermelha Patamar 2",
                        }
                        nome_bandeira = mapa_bandeiras.get(bandeira_acionada, bandeira_acionada)
                        _LOGGER.info(
                            f"Bandeira vigente encontrada: {nome_bandeira} "
                            f"(competência: {dat_competencia}, adicional: {valor_adicional})"
                        )
                        return nome_bandeira, valor_adicional, dat_competencia

        except aiohttp.ClientError as err:
            _LOGGER.warning(f"Erro ao acessar API SQL de bandeiras: {err}")
        except Exception as err:
            _LOGGER.warning(f"Erro inesperado ao processar bandeira: {err}")

        _LOGGER.error("Não foi possível obter a bandeira vigente.")
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
        Busca a bandeira vigente e a tarifa base, calcula a tarifa final
        para a bandeira vigente e atualiza o banco de dados.
        """
        hoje = date.today()
        _LOGGER.info(f"Iniciando atualização de tarifas para '{concessionaria_nome}' via SQL em {hoje}.")

        resultado_bandeira = await self.async_get_bandeira_vigente(hoje)
        if resultado_bandeira is None:
            _LOGGER.warning(
                "API não retornou a bandeira vigente. Tentando fallback no banco de dados."
            )
            resultado_bandeira = await self._db.async_get_latest_bandeira()
            if resultado_bandeira is None:
                _LOGGER.error(
                    "Não foi possível obter a bandeira vigente via API ou banco. Abortando atualização."
                )
                return None
            _LOGGER.info("Bandeira vigente obtida via fallback do banco de dados.")

        nome_raw, valor_adicional, dat_competencia = resultado_bandeira
        mapa_bandeiras = {
            "Verde": "Bandeira Verde",
            "Amarela": "Bandeira Amarela",
            "Vermelha P1": "Bandeira Vermelha Patamar 1",
            "Vermelha P2": "Bandeira Vermelha Patamar 2",
        }
        bandeira_vigente = mapa_bandeiras.get(nome_raw, nome_raw)

        tarifa_base = None
        
        # Monta a query SQL com os filtros especificados e busca a data mais recente
        sql_query = (
            f'WITH ultima_data AS ('
            f'  SELECT MAX("DatFimVigencia") as data_max '
            f'  FROM "{RESOURCE_ID_TARIFAS}" '
            f'  WHERE "SigAgente" = \'{concessionaria_nome}\' '
            f'  AND "DscBaseTarifaria" = \'Tarifa de Aplicação\' '
            f'  AND "DscSubGrupo" = \'B1\' '
            f'  AND "DscClasse" = \'Residencial\' '
            f') '
            f'SELECT "VlrTUSD", "VlrTE" '
            f'FROM "{RESOURCE_ID_TARIFAS}" '
            f'WHERE "SigAgente" = \'{concessionaria_nome}\' '
            f'AND "DscBaseTarifaria" = \'Tarifa de Aplicação\' '
            f'AND "DscSubGrupo" = \'B1\' '
            f'AND "DscClasse" = \'Residencial\' '
            f'AND "DscModalidadeTarifaria" = \'Convencional\' '
            f'AND "DscSubClasse" = \'Residencial\' '
            f'AND "DscDetalhe" = \'Não se aplica\' '
            f'AND "DatFimVigencia" = (SELECT data_max FROM ultima_data) '
            f'LIMIT 1'
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

        # Calcula a tarifa para a bandeira vigente (converte de R$/MWh para R$/kWh)
        tarifa_final = (tarifa_base + valor_adicional) / 1000

        snapshot = await self._db.async_save_tarifa_snapshot(
            concessionaria_nome, bandeira_vigente, tarifa_final, dat_competencia, "online"
        )
        _LOGGER.info(
            f"Tarifa final para {concessionaria_nome} ({bandeira_vigente}): {tarifa_final:.6f} R$/kWh"
        )
        return snapshot
