"""API Client para a integração Tarifas de Energia Brasil."""

import csv
from datetime import date, datetime
import logging

import aiohttp

from ..utils.database import DatabaseManager

_LOGGER = logging.getLogger(__name__)

URL_SQL_API = "https://dadosabertos.aneel.gov.br/api/3/action/datastore_search_sql"
URL_BANDEIRAS_CSV = "https://dadosabertos.aneel.gov.br/dataset/7f43a020-6dc5-44b8-80b4-d97eaa94436c/resource/0591b8f6-fe54-437b-b72b-1aa2efd46e42/download/bandeira-tarifaria-acionamento.csv"

RESOURCE_ID_TARIFAS = "fcf2906c-7c32-4b9b-a637-054e7a5234f4"
RESOURCE_ID_BANDEIRAS = "0591b8f6-fe54-437b-b72b-1aa2efd46e42"


class TarifasDeEnergiaBrasilAPI:
    """Cliente para buscar dados de tarifas e gerenciar o banco de dados."""

    def __init__(self, hass, session: aiohttp.ClientSession, db_manager: DatabaseManager):
        self._hass = hass
        self._session = session
        self._db = db_manager

    @staticmethod
    def _parse_float_br(valor: str) -> float:
        valor_normalizado = valor.strip().replace(".", "").replace(",", ".")
        if valor_normalizado.startswith("."):
            valor_normalizado = f"0{valor_normalizado}"
        if not valor_normalizado:
            return 0.0
        return float(valor_normalizado)

    async def async_preload_latest_bandeira_csv(self) -> bool:
        """Faz pre-load da última linha do CSV de bandeiras."""
        try:
            async with self._session.get(URL_BANDEIRAS_CSV) as response:
                response.raise_for_status()
                csv_bytes = await response.read()

            csv_text = None
            for encoding in [(response.charset or "").strip(), "utf-8-sig", "utf-8", "cp1252", "latin-1"]:
                if not encoding:
                    continue
                try:
                    csv_text = csv_bytes.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue

            if csv_text is None:
                return False

            linhas = [
                row for row in csv.reader(csv_text.splitlines(), delimiter=";") if len(row) >= 4 and row[1].strip()
            ]
            if not linhas:
                return False

            ultima_linha = linhas[-1]
            data_geracao = datetime.strptime(ultima_linha[0].strip(), "%Y-%m-%d").date()
            data_competencia = datetime.strptime(ultima_linha[1].strip(), "%Y-%m-%d").date()
            nome_bandeira = ultima_linha[2].strip()
            valor_adicional = self._parse_float_br(ultima_linha[3]) / 1000.0

            return await self._db.async_insert_bandeira_csv_row_if_newer(
                data_geracao, data_competencia, nome_bandeira, valor_adicional
            )

        except Exception as err:
            _LOGGER.warning("Falha ao baixar CSV de bandeiras: %s", err)
            return False

    async def async_get_bandeira_vigente(self, competencia: date) -> tuple[str, float, date] | None:
        hoje = competencia.strftime("%Y-%m-%d")
        sql_query = f'SELECT "NomBandeiraAcionada", "VlrAdicionalBandeira", "DatCompetencia" FROM "{RESOURCE_ID_BANDEIRAS}" WHERE "DatCompetencia" <= \'{hoje}\' ORDER BY "DatCompetencia" DESC LIMIT 1'
        try:
            async with self._session.get(URL_SQL_API, params={"sql": sql_query}) as response:
                response.raise_for_status()
                data = await response.json()
                if data.get("success") and data.get("result", {}).get("records"):
                    record = data["result"]["records"][0]
                    bandeira_acionada = record.get("NomBandeiraAcionada")
                    valor_adicional = self._parse_float_br(str(record.get("VlrAdicionalBandeira", "0"))) / 1000.0
                    dat_competencia = datetime.strptime(str(record.get("DatCompetencia", ""))[:10], "%Y-%m-%d").date()

                    mapa_bandeiras = {
                        "Verde": "Bandeira Verde",
                        "Amarela": "Bandeira Amarela",
                        "Vermelha P1": "Bandeira Vermelha Patamar 1",
                        "Vermelha P2": "Bandeira Vermelha Patamar 2",
                    }
                    nome_bandeira = mapa_bandeiras.get(bandeira_acionada, bandeira_acionada)
                    return nome_bandeira, valor_adicional, dat_competencia
        except Exception as err:
            _LOGGER.warning(f"Erro SQL bandeiras: {err}")
        return None

    async def async_fetch_concessionarias(self) -> bool:
        try:
            async with self._session.get(
                URL_SQL_API, params={"sql": f'SELECT "SigAgente" from "{RESOURCE_ID_TARIFAS}" group by "SigAgente"'}
            ) as response:
                data = await response.json()
                if data.get("success"):
                    nomes = {r["SigAgente"] for r in data["result"].get("records", []) if "SigAgente" in r}
                    if nomes:
                        await self._db.async_update_concessionarias(nomes)
                        return True
        except Exception as err:
            _LOGGER.error(f"Erro buscar concessionárias: {err}")
        return False

    async def async_fetch_tarifas_base(self, concessionaria_nome: str) -> dict | None:
        """Busca TE e TUSD (Convencional) para uma concessionária."""
        sql_query = (
            f'WITH ultima_data AS (SELECT MAX("DatFimVigencia") as data_max FROM "{RESOURCE_ID_TARIFAS}" WHERE "SigAgente" = \'{concessionaria_nome}\' AND "DscBaseTarifaria" = \'Tarifa de Aplicação\' AND "DscSubGrupo" = \'B1\' AND "DscClasse" = \'Residencial\') '
            f'SELECT "VlrTUSD", "VlrTE" FROM "{RESOURCE_ID_TARIFAS}" WHERE "SigAgente" = \'{concessionaria_nome}\' AND "DscBaseTarifaria" = \'Tarifa de Aplicação\' AND "DscSubGrupo" = \'B1\' AND "DscClasse" = \'Residencial\' AND "DscModalidadeTarifaria" = \'Convencional\' AND "DscSubClasse" = \'Residencial\' AND "DscDetalhe" = \'Não se aplica\' AND "DatFimVigencia" = (SELECT data_max FROM ultima_data) LIMIT 1'
        )
        try:
            async with self._session.get(URL_SQL_API, params={"sql": sql_query}) as response:
                data = await response.json()
                if data.get("success") and data.get("result", {}).get("records"):
                    record = data["result"]["records"][0]
                    return {
                        "te": self._parse_float_br(str(record.get("VlrTE", "0"))) / 1000.0,
                        "tusd": self._parse_float_br(str(record.get("VlrTUSD", "0"))) / 1000.0,
                    }
        except Exception as err:
            _LOGGER.error(f"Erro fetch tarifas: {err}")
        return None
