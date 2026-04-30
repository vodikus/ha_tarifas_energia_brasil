"""Scraper para concessionárias da família CPFL."""

import logging

from .base import BaseScraper

_LOGGER = logging.getLogger(__name__)

URL_CPFL_PAULISTA = "https://www.cpfl.com.br/paulista/pis-cofins"
URL_CPFL_PIRATININGA = "https://www.cpfl.com.br/piratininga/pis-cofins"


class CpflScraper(BaseScraper):
    """Scraper para as concessionárias CPFL."""

    def __init__(self, session, concessionaria_nome):
        super().__init__(session)
        self.concessionaria_nome = concessionaria_nome

    async def async_get_impostos(self) -> dict:
        url = URL_CPFL_PIRATININGA if "PIRATININGA" in self.concessionaria_nome.upper() else URL_CPFL_PAULISTA

        try:
            async with self._session.get(url, timeout=10) as response:
                if response.status != 200:
                    return None
                html_content = await response.text()

            texto = self.normalize_text(html_content)
            pis = self.extract_percent_near_keywords(texto, ("PIS", "PIS/PASEP"))
            cofins = self.extract_percent_near_keywords(texto, ("COFINS",))

            # O ICMS da CPFL Residencial em SP costuma ter faixas. O scraper simplificado
            # não vai conseguir adivinhar a faixa exata do cliente, por isso o ICMS
            # é frequentemente fixado pelo usuário na UI. Vamos retornar None para ICMS para
            # indicar que ele não extraiu e manter o valor que estava antes.

            return {
                "pis": pis if pis > 0 else None,
                "cofins": cofins if cofins > 0 else None,
                "icms": None,  # ICMS na CPFL precisa de fallback manual/config
            }
        except Exception as err:
            _LOGGER.error(f"Erro no scraper CPFL: {err}")
            return None
