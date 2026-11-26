"""Configuração de testes: usa o harness oficial de custom components do Home Assistant."""

import pytest

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def stable_calendar(freezer):
    """Fixtures da API são de novembro; testes não dependem do relógio da máquina."""
    freezer.move_to("2026-11-26T12:00:00+00:00")


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Permite carregar custom_components/tarifas_energia_brasil nos testes."""
    yield


@pytest.fixture(autouse=True)
def isolated_tarifas_db(hass):
    """Remove o SQLite de cache antes de cada teste: o harness reutiliza o mesmo config_dir."""
    import os

    db_path = hass.config.path("tarifas_energia_brasil.sqlite")
    if os.path.exists(db_path):
        os.remove(db_path)
    yield
    if os.path.exists(db_path):
        os.remove(db_path)
