"""Schema para configuração da Tarifa Branca."""

from typing import Any

import voluptuous as vol

from homeassistant.helpers import selector

from ...const import (
    CONF_TB_FERIADOS_EXTRAS,
    CONF_TB_INTER1_FIM,
    CONF_TB_INTER1_INI,
    CONF_TB_INTER2_FIM,
    CONF_TB_INTER2_INI,
    CONF_TB_PONTA_FIM,
    CONF_TB_PONTA_INI,
)

# Horários padrão Resolução ANEEL 1000/2021 (Horário de Brasília)
_DEFAULT_PONTA_INI = "18:00:00"
_DEFAULT_PONTA_FIM = "21:00:00"
_DEFAULT_INTER1_INI = "17:30:00"
_DEFAULT_INTER1_FIM = "18:00:00"
_DEFAULT_INTER2_INI = "21:00:00"
_DEFAULT_INTER2_FIM = "21:30:00"

_TIME_SELECTOR = selector.TimeSelector()
_TEXT_SELECTOR = selector.TextSelector(selector.TextSelectorConfig(multiline=True))


def get_tarifa_branca_schema(options: dict[str, Any]) -> vol.Schema:
    """Retorna o schema para configuração dos horários da Tarifa Branca."""
    return vol.Schema(
        {
            vol.Optional(
                CONF_TB_PONTA_INI,
                default=options.get(CONF_TB_PONTA_INI, _DEFAULT_PONTA_INI),
            ): _TIME_SELECTOR,
            vol.Optional(
                CONF_TB_PONTA_FIM,
                default=options.get(CONF_TB_PONTA_FIM, _DEFAULT_PONTA_FIM),
            ): _TIME_SELECTOR,
            vol.Optional(
                CONF_TB_INTER1_INI,
                default=options.get(CONF_TB_INTER1_INI, _DEFAULT_INTER1_INI),
            ): _TIME_SELECTOR,
            vol.Optional(
                CONF_TB_INTER1_FIM,
                default=options.get(CONF_TB_INTER1_FIM, _DEFAULT_INTER1_FIM),
            ): _TIME_SELECTOR,
            vol.Optional(
                CONF_TB_INTER2_INI,
                default=options.get(CONF_TB_INTER2_INI, _DEFAULT_INTER2_INI),
            ): _TIME_SELECTOR,
            vol.Optional(
                CONF_TB_INTER2_FIM,
                default=options.get(CONF_TB_INTER2_FIM, _DEFAULT_INTER2_FIM),
            ): _TIME_SELECTOR,
            vol.Optional(
                CONF_TB_FERIADOS_EXTRAS,
                default=options.get(CONF_TB_FERIADOS_EXTRAS, ""),
            ): _TEXT_SELECTOR,
        }
    )
