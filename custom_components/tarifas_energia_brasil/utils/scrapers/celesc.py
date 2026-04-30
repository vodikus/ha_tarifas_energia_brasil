"""Scraper para concessionária CELESC."""

import logging
import re

from .base import BaseScraper

_LOGGER = logging.getLogger(__name__)

URL_CELESC = "https://www.celesc.com.br/tarifas-de-energia"


class CelescScraper(BaseScraper):
    """Scraper para a concessionária CELESC."""

    def __init__(self, session, concessionaria_nome):
        super().__init__(session)
        self.concessionaria_nome = concessionaria_nome

    async def async_get_impostos(self) -> dict:
        try:
            async with self._session.get(URL_CELESC, timeout=10) as response:
                if response.status != 200:
                    return None
                html_content = await response.text()

            texto = self.normalize_text(html_content)

            # A CELESC apresenta uma tabela com as colunas PIS e COFINS mês a mês.
            # O layout lido será aproximadamente: "PIS COFINS 04/2026 0,35% 1,63%"
            match = re.search(r"pis\s*cofins\s*\d{2}/\d{4}\s*(\d+[,.]\d+)\s*%\s*(\d+[,.]\d+)\s*%", texto, re.IGNORECASE)

            if match:
                pis = float(match.group(1).replace(",", "."))
                cofins = float(match.group(2).replace(",", "."))
                return {
                    "pis": pis if pis > 0 else None,
                    "cofins": cofins if cofins > 0 else None,
                    "icms": None,  # ICMS em SC depende da faixa de consumo, usuário precisa configurar
                }

            _LOGGER.warning("Não foi possível encontrar a tabela de PIS/COFINS na CELESC.")
            return None

        except Exception as err:
            _LOGGER.error(f"Erro no scraper CELESC: {err}")
            return None
