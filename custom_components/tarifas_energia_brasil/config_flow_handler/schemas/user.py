"""Schemas para validação do Config Flow do usuário."""

import voluptuous as vol

from ...const import CONF_CONCESSIONARIA


def get_user_schema(lista_concessionarias: list[str]) -> vol.Schema:
    """Retorna o schema para o passo do usuário."""
    return vol.Schema({vol.Required(CONF_CONCESSIONARIA): vol.In(sorted(lista_concessionarias))})
