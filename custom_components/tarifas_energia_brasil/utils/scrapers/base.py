"""Módulo base para scrapers de impostos das concessionárias."""

from abc import ABC, abstractmethod
import html
import re
import unicodedata

import aiohttp


class BaseScraper(ABC):
    """Classe base para todos os scrapers de concessionárias."""

    def __init__(self, session: aiohttp.ClientSession):
        self._session = session

    @abstractmethod
    async def async_get_impostos(self) -> dict:
        """Deve retornar um dict com as alíquotas {'pis': float, 'cofins': float, 'icms': float} ou None."""

    # -- Funções utilitárias herdadas para os scrapers filhos --

    @staticmethod
    def normalize_text(raw: str) -> str:
        """Normaliza texto HTML para busca."""
        no_script = re.sub(r"<script.*?>.*?</script>", " ", raw, flags=re.IGNORECASE | re.DOTALL)
        no_style = re.sub(r"<style.*?>.*?</style>", " ", no_script, flags=re.IGNORECASE | re.DOTALL)
        no_tags = re.sub(r"<[^>]+>", " ", no_style)
        unescaped = html.unescape(no_tags)
        return re.sub(r"\s+", " ", unescaped).strip()

    @staticmethod
    def normalize_key(text: str) -> str:
        """Remove acentos e minúsculas."""
        lowered = unicodedata.normalize("NFKD", text.lower())
        return "".join(ch for ch in lowered if not unicodedata.combining(ch))

    @staticmethod
    def extract_percent_near_keywords(text: str, keywords: tuple[str, ...], window: int = 120) -> float:
        """Extrai percentual próximo de palavras-chave."""
        norm_text = BaseScraper.normalize_key(text)
        for keyword in keywords:
            keyword_norm = BaseScraper.normalize_key(keyword)
            index = norm_text.find(keyword_norm)
            if index < 0:
                continue

            excerpt = norm_text[max(index - window, 0) : index + window]
            match = re.search(rf"{re.escape(keyword_norm)}.{{0,80}}?(\d{{1,2}}(?:[.,]\d{{1,4}})?)\s*%", excerpt)
            if match:
                return float(match.group(1).replace(",", "."))

            match_back = re.search(
                rf"(\d{{1,2}}(?:[.,]\d{{1,4}})?)\s*%[^0-9]{{0,80}}{re.escape(keyword_norm)}", excerpt
            )
            if match_back:
                return float(match_back.group(1).replace(",", "."))
        return 0.0
