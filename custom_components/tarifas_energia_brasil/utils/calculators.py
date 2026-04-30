"""Calculadoras para regras matemáticas de tarifas, tributos e SCEE."""

from ..const import DISPONIBILIDADE


def percent_to_decimal(percent: float) -> float:
    """Converte percentual para decimal (ex: 12 -> 0.12)."""
    if percent is None:
        return 0.0
    return percent / 100.0


def aplicar_tributos_por_dentro(
    valor_sem_tributos: float, pis_decimal: float, cofins_decimal: float, icms_decimal: float
) -> float:
    """Aplica tributos por dentro (fórmula padrão do setor elétrico)."""
    soma_aliquotas = pis_decimal + cofins_decimal + icms_decimal
    if soma_aliquotas >= 1:
        return valor_sem_tributos  # Evita divisão por zero ou valor negativo
    return valor_sem_tributos / (1 - soma_aliquotas)


def calcular_tarifa_final(te: float, tusd: float, pis: float, cofins: float, icms: float) -> float:
    """Calcula a tarifa final com tributos embutidos."""
    tarifa_bruta = te + tusd
    return aplicar_tributos_por_dentro(
        tarifa_bruta, percent_to_decimal(pis), percent_to_decimal(cofins), percent_to_decimal(icms)
    )


def custo_disponibilidade(tipo_fornecimento: str, tarifa_final: float) -> float:
    """Calcula o custo monetário da disponibilidade."""
    minimo_kwh = DISPONIBILIDADE.get(tipo_fornecimento, 50.0)
    return minimo_kwh * tarifa_final


def calcular_fatura_estimada(
    consumo_kwh: float,
    geracao_kwh: float,
    injecao_kwh: float,
    saldo_anterior_kwh: float,
    tarifa_final: float,
    fio_b_final: float,
    tipo_fornecimento: str,
) -> dict:
    """
    Calcula os valores da fatura e os novos saldos considerando o SCEE (Sistema de Compensação).
    Se injecao_kwh não for informada, assume geracao_kwh como injeção total ou vice-versa.
    """
    consumo = max(consumo_kwh or 0.0, 0.0)
    injecao = max(injecao_kwh or geracao_kwh or 0.0, 0.0)
    geracao = max(geracao_kwh or injecao_kwh or 0.0, 0.0)
    saldo_anterior = max(saldo_anterior_kwh or 0.0, 0.0)

    energia_disponivel = saldo_anterior + injecao
    energia_compensada = min(consumo, energia_disponivel)

    energia_nao_compensada = max(consumo - energia_compensada, 0.0)

    valor_energia_nao_compensada = energia_nao_compensada * tarifa_final
    valor_fio_b = energia_compensada * fio_b_final

    valor_consumo = valor_energia_nao_compensada + valor_fio_b

    # Custo de disponibilidade
    minimo_kwh = DISPONIBILIDADE.get(tipo_fornecimento, 50.0)
    valor_disponibilidade = minimo_kwh * tarifa_final

    # Fatura final (o maior entre o consumo medido/compensado e a taxa mínima)
    fatura_estimada_r = max(valor_disponibilidade, valor_consumo)

    # Kwh "comprado" compulsoriamente se o consumo nao atingiu o minimo.
    # Este valor garante o piso de faturamento, mas NAO gera creditos SCEE,
    # pois creditos somente surgem de injecao excedente na rede.
    kwh_comprado_minimo = max(minimo_kwh - energia_nao_compensada, 0.0)  # noqa: F841 (mantido para clareza)

    # Novo saldo: creditos gerados exclusivamente por injecao excedente
    credito_gerado = max(injecao - energia_compensada, 0.0)
    novo_saldo_kwh = saldo_anterior - min(saldo_anterior, energia_compensada) + credito_gerado

    auto_consumo = max(geracao - injecao, 0.0)

    return {
        "fatura_estimada_r": fatura_estimada_r,
        "energia_compensada_kwh": energia_compensada,
        "energia_nao_compensada_kwh": energia_nao_compensada,
        "novo_saldo_kwh": novo_saldo_kwh,
        "auto_consumo_kwh": auto_consumo,
    }
