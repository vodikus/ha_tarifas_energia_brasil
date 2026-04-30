"""Data processing utilities for the coordinator.

This module provides functions for processing, transforming, and validating
data received from the API before distributing it to entities.

It implements the "Quebra de Cálculo" (billing cycle reset) logic, which
subtracts a stored baseline from the raw entity values so that sensors with
lifetime-accumulated totals are correctly handled on a per-period basis.
"""

from datetime import date, datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from ..const import (
    CICLO_DIARIO,
    CICLO_SEMANAL,
    CONF_ALIQUOTA_COFINS,
    CONF_ALIQUOTA_ICMS,
    CONF_ALIQUOTA_PIS,
    CONF_CICLO_QUEBRA,
    CONF_DIA_LEITURA,
    CONF_ENTIDADE_CONSUMO,
    CONF_ENTIDADE_GERACAO,
    CONF_ENTIDADE_INJECAO,
    CONF_TIPO_FORNECIMENTO,
    DEFAULT_CICLO,
    DEFAULT_DIA_LEITURA,
    DEFAULT_TIPO_FORNECIMENTO,
    DISPONIBILIDADE,
)
from ..utils.calculators import calcular_fatura_estimada, calcular_tarifa_final


def get_state_float(hass: HomeAssistant, entity_id: str | None) -> float:
    """Pega o estado de uma entidade do HA de forma segura."""
    if not entity_id:
        return 0.0
    state = hass.states.get(entity_id)
    if state and state.state not in ["unknown", "unavailable"]:
        try:
            return float(state.state)
        except ValueError:
            pass
    return 0.0


def _is_reset_due(
    ultimo_reset_iso: str | None,
    ciclo: str,
    dia_leitura: int,
    now: date,
) -> bool:
    """Verifica se o ciclo de leitura deve ser resetado.

    Regras:
    - diario: Reseta todo dia (último reset foi em dia diferente do atual).
    - semanal: Reseta quando o dia da semana ISO (1=Seg, 7=Dom) corresponde
      ao dia_leitura configurado e o último reset foi em semana anterior.
    - mensal: Reseta quando o dia do mês atual >= dia_leitura e o último reset
      ocorreu em mês/ano anterior ao período corrente de leitura.
    """
    if not ultimo_reset_iso:
        return True

    try:
        ultimo_reset = date.fromisoformat(ultimo_reset_iso)
    except ValueError:
        return True

    if ciclo == CICLO_DIARIO:
        return ultimo_reset < now

    if ciclo == CICLO_SEMANAL:
        # dia_leitura: 1=Segunda ... 7=Domingo (ISO weekday)
        dia_efetivo = max(1, min(7, dia_leitura))
        inicio_semana_atual = date.fromisocalendar(now.year, now.isocalendar()[1], dia_efetivo)
        return ultimo_reset < inicio_semana_atual and now >= inicio_semana_atual

    # CICLO_MENSAL (padrão)
    # Calcula o início do período de leitura vigente
    if now.day >= dia_leitura:
        inicio_periodo = date(now.year, now.month, dia_leitura)
    elif now.month == 1:
        inicio_periodo = date(now.year - 1, 12, dia_leitura)
    else:
        import calendar

        last_day_prev = calendar.monthrange(now.year, now.month - 1)[1]
        dia_efetivo = min(dia_leitura, last_day_prev)
        inicio_periodo = date(now.year, now.month - 1, dia_efetivo)

    return ultimo_reset < inicio_periodo


def process_coordinator_data(
    hass: HomeAssistant,
    entry: ConfigEntry,
    snapshot: dict,
    local_data: dict,
) -> tuple[dict, dict]:
    """Processa os dados brutos e gera o dicionário de estado final e o local_data atualizado.

    Implementa a lógica de Quebra de Cálculo:
    - Armazena um baseline (snapshot do início do período) em local_data.
    - Subtrai o baseline dos valores atuais para calcular o consumo efetivo do período.
    - Reseta o baseline automaticamente quando um novo ciclo começa.
    """
    pis = snapshot.get("aliquota_pis") or entry.options.get(CONF_ALIQUOTA_PIS, 0.0)
    cofins = snapshot.get("aliquota_cofins") or entry.options.get(CONF_ALIQUOTA_COFINS, 0.0)
    icms = snapshot.get("aliquota_icms") or entry.options.get(CONF_ALIQUOTA_ICMS, 0.0)

    tarifa_te = snapshot.get("tarifa_base_te", 0.0)
    tarifa_tusd = snapshot.get("tarifa_base_tusd", 0.0)
    tarifa_base = tarifa_te + tarifa_tusd

    bandeira_vigente = snapshot.get("bandeira_vigente", "Bandeira Verde")

    fio_b_final = calcular_tarifa_final(0, tarifa_tusd * 0.3, pis, cofins, icms)
    tarifa_vigente_final = calcular_tarifa_final(tarifa_te, tarifa_tusd, pis, cofins, icms)

    # Leituras brutas das entidades
    consumo_kwh_bruto = get_state_float(hass, entry.options.get(CONF_ENTIDADE_CONSUMO))
    geracao_kwh_bruto = get_state_float(hass, entry.options.get(CONF_ENTIDADE_GERACAO))
    injecao_kwh_bruto = get_state_float(hass, entry.options.get(CONF_ENTIDADE_INJECAO))

    # Quebra de Cálculo: verificar se o ciclo deve ser resetado
    ciclo = entry.options.get(CONF_CICLO_QUEBRA, DEFAULT_CICLO)
    dia_leitura = int(entry.options.get(CONF_DIA_LEITURA, DEFAULT_DIA_LEITURA))
    hoje = datetime.now().date()

    local_data_updated = dict(local_data)

    if _is_reset_due(local_data.get("ultimo_reset"), ciclo, dia_leitura, hoje):
        # Novo ciclo: gravar baseline e transferir saldo residual de créditos
        local_data_updated["baseline_consumo"] = consumo_kwh_bruto
        local_data_updated["baseline_geracao"] = geracao_kwh_bruto
        local_data_updated["baseline_injecao"] = injecao_kwh_bruto
        local_data_updated["saldo_anterior_kwh"] = local_data.get("saldo_atual_kwh", 0.0)
        local_data_updated["ultimo_reset"] = hoje.isoformat()

    # Consumo efetivo do período = bruto − baseline do início do ciclo
    baseline_consumo = local_data_updated.get("baseline_consumo", consumo_kwh_bruto)
    baseline_geracao = local_data_updated.get("baseline_geracao", geracao_kwh_bruto)
    baseline_injecao = local_data_updated.get("baseline_injecao", injecao_kwh_bruto)

    consumo_kwh = max(0.0, consumo_kwh_bruto - baseline_consumo)
    geracao_kwh = max(0.0, geracao_kwh_bruto - baseline_geracao)
    injecao_kwh = max(0.0, injecao_kwh_bruto - baseline_injecao)

    saldo_anterior_kwh = local_data_updated.get("saldo_anterior_kwh", 0.0)
    tipo_forn = entry.options.get(CONF_TIPO_FORNECIMENTO, DEFAULT_TIPO_FORNECIMENTO)

    calc = calcular_fatura_estimada(
        consumo_kwh, geracao_kwh, injecao_kwh, saldo_anterior_kwh, tarifa_vigente_final, fio_b_final, tipo_forn
    )

    local_data_updated["saldo_atual_kwh"] = calc["novo_saldo_kwh"]

    consumo_minimo_kwh = float(DISPONIBILIDADE.get(tipo_forn, 50))

    processed_data = {
        "bandeira_vigente": bandeira_vigente,
        "tarifa_vigente_final": tarifa_vigente_final,
        "tarifa_base_aneel": tarifa_base,
        "fio_b_final": fio_b_final,
        "aliquota_pis": pis,
        "aliquota_cofins": cofins,
        "aliquota_icms": icms,
        "api_status": snapshot["api_status"],
        "timestamp": snapshot["timestamp"],
        "fatura_estimada_r": calc["fatura_estimada_r"],
        "energia_compensada_kwh": calc["energia_compensada_kwh"],
        "energia_nao_compensada_kwh": calc["energia_nao_compensada_kwh"],
        "saldo_creditos_kwh": calc["novo_saldo_kwh"],
        "auto_consumo_estimado": calc["auto_consumo_kwh"],
        "consumo_minimo_kwh": consumo_minimo_kwh,
        "ciclo_inicio": local_data_updated.get("ultimo_reset"),
    }

    return processed_data, local_data_updated
