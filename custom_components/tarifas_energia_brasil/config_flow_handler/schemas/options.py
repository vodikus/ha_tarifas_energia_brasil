"""Schemas para validação do Options Flow."""

from typing import Any

import voluptuous as vol

from homeassistant.helpers import selector

from ...const import (
    CICLO_DIARIO,
    CICLO_MENSAL,
    CICLO_SEMANAL,
    CONF_ALIQUOTA_COFINS,
    CONF_ALIQUOTA_ICMS,
    CONF_ALIQUOTA_PIS,
    CONF_CICLO_QUEBRA,
    CONF_DIA_LEITURA,
    CONF_ENTIDADE_CONSUMO,
    CONF_ENTIDADE_GERACAO,
    CONF_ENTIDADE_INJECAO,
    CONF_MODALIDADE_TARIFARIA,
    CONF_MODO_IMPOSTOS,
    CONF_TIPO_FORNECIMENTO,
    DEFAULT_CICLO,
    DEFAULT_DIA_LEITURA,
    DEFAULT_MODALIDADE,
    DEFAULT_TIPO_FORNECIMENTO,
    FORNECIMENTO_BIFASICO,
    FORNECIMENTO_MONOFASICO,
    FORNECIMENTO_TRIFASICO,
    MODALIDADE_BRANCA,
    MODALIDADE_CONVENCIONAL,
    MODO_IMPOSTOS_AUTOMATICO,
    MODO_IMPOSTOS_MANUAL,
)


def get_options_schema(options: dict[str, Any], suporta_automatico: bool) -> vol.Schema:
    """Retorna o schema para o passo de opções gerais."""
    modos_imposto = [MODO_IMPOSTOS_MANUAL]
    if suporta_automatico:
        modos_imposto.append(MODO_IMPOSTOS_AUTOMATICO)

    return vol.Schema(
        {
            vol.Optional(
                CONF_MODALIDADE_TARIFARIA, default=options.get(CONF_MODALIDADE_TARIFARIA, DEFAULT_MODALIDADE)
            ): vol.In([MODALIDADE_CONVENCIONAL, MODALIDADE_BRANCA]),
            vol.Optional(
                CONF_TIPO_FORNECIMENTO, default=options.get(CONF_TIPO_FORNECIMENTO, DEFAULT_TIPO_FORNECIMENTO)
            ): vol.In([FORNECIMENTO_MONOFASICO, FORNECIMENTO_BIFASICO, FORNECIMENTO_TRIFASICO]),
            vol.Optional(
                CONF_ENTIDADE_CONSUMO, description={"suggested_value": options.get(CONF_ENTIDADE_CONSUMO)}
            ): selector.EntitySelector(selector.EntitySelectorConfig(domain=["sensor", "input_number"])),
            vol.Optional(
                CONF_ENTIDADE_GERACAO, description={"suggested_value": options.get(CONF_ENTIDADE_GERACAO)}
            ): selector.EntitySelector(selector.EntitySelectorConfig(domain=["sensor", "input_number"])),
            vol.Optional(
                CONF_ENTIDADE_INJECAO, description={"suggested_value": options.get(CONF_ENTIDADE_INJECAO)}
            ): selector.EntitySelector(selector.EntitySelectorConfig(domain=["sensor", "input_number"])),
            vol.Optional(
                CONF_MODO_IMPOSTOS,
                default=options.get(
                    CONF_MODO_IMPOSTOS, MODO_IMPOSTOS_AUTOMATICO if suporta_automatico else MODO_IMPOSTOS_MANUAL
                ),
            ): vol.In(modos_imposto),
            vol.Optional(
                CONF_CICLO_QUEBRA,
                default=options.get(CONF_CICLO_QUEBRA, DEFAULT_CICLO),
            ): vol.In([CICLO_MENSAL, CICLO_SEMANAL, CICLO_DIARIO]),
            vol.Optional(
                CONF_DIA_LEITURA,
                default=options.get(CONF_DIA_LEITURA, DEFAULT_DIA_LEITURA),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=31, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
        }
    )


def get_manual_taxes_schema(options: dict[str, Any]) -> vol.Schema:
    """Retorna o schema para o preenchimento manual de impostos."""
    return vol.Schema(
        {
            vol.Optional(CONF_ALIQUOTA_PIS, default=options.get(CONF_ALIQUOTA_PIS, 0.0)): vol.Coerce(float),
            vol.Optional(CONF_ALIQUOTA_COFINS, default=options.get(CONF_ALIQUOTA_COFINS, 0.0)): vol.Coerce(float),
            vol.Optional(CONF_ALIQUOTA_ICMS, default=options.get(CONF_ALIQUOTA_ICMS, 0.0)): vol.Coerce(float),
        }
    )
