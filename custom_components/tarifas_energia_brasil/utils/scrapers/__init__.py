"""Registro e fábrica de scrapers de impostos."""

from .base import BaseScraper
from .celesc import CelescScraper
from .cpfl import CpflScraper


def get_scraper(concessionaria_nome: str, session) -> BaseScraper | None:
    """Retorna a classe do scraper apropriada com base no nome da concessionária, ou None se não houver."""
    nome_upper = concessionaria_nome.upper()

    if "CPFL" in nome_upper:
        return CpflScraper(session, concessionaria_nome)

    if "CELESC" in nome_upper:
        return CelescScraper(session, concessionaria_nome)

    return None


def has_scraper(concessionaria_nome: str) -> bool:
    """Verifica se há scraper automático para a concessionária."""
    return get_scraper(concessionaria_nome, None) is not None
