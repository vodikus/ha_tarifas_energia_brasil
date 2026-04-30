"""Constantes para a integração Tarifas de Energia Brasil."""

DOMAIN = "tarifas_energia_brasil"

# Configuração Básica
CONF_CONCESSIONARIA = "concessionaria"

# Configuração Avançada (Options Flow)
CONF_MODALIDADE_TARIFARIA = "modalidade_tarifaria"
CONF_ENTIDADE_CONSUMO = "entidade_consumo"
CONF_ENTIDADE_GERACAO = "entidade_geracao"
CONF_ENTIDADE_INJECAO = "entidade_injecao"
CONF_TIPO_FORNECIMENTO = "tipo_fornecimento"  # monofasico, bifasico, trifasico
CONF_MODO_IMPOSTOS = "modo_impostos"  # automatico, manual
CONF_ALIQUOTA_PIS = "aliquota_pis"
CONF_ALIQUOTA_COFINS = "aliquota_cofins"
CONF_ALIQUOTA_ICMS = "aliquota_icms"
CONF_CICLO_QUEBRA = "ciclo_quebra"
CONF_DIA_LEITURA = "dia_leitura"

# Tarifa Branca — janelas de horário e feriados extras
CONF_TB_PONTA_INI = "tb_ponta_ini"
CONF_TB_PONTA_FIM = "tb_ponta_fim"
CONF_TB_INTER1_INI = "tb_inter1_ini"
CONF_TB_INTER1_FIM = "tb_inter1_fim"
CONF_TB_INTER2_INI = "tb_inter2_ini"
CONF_TB_INTER2_FIM = "tb_inter2_fim"
CONF_TB_FERIADOS_EXTRAS = "tb_feriados_extras"

# Valores Padrões
DEFAULT_MODALIDADE = "convencional"
DEFAULT_TIPO_FORNECIMENTO = "bifasico"
DEFAULT_MODO_IMPOSTOS = "manual"
DEFAULT_CICLO = "mensal"
DEFAULT_DIA_LEITURA = 1

# Modalidades Tarifárias
MODALIDADE_CONVENCIONAL = "convencional"
MODALIDADE_BRANCA = "branca"

# Modos de Impostos
MODO_IMPOSTOS_AUTOMATICO = "automatico"
MODO_IMPOSTOS_MANUAL = "manual"

# Ciclos de Quebra
CICLO_DIARIO = "diario"
CICLO_SEMANAL = "semanal"
CICLO_MENSAL = "mensal"

# Tipos de Fornecimento
FORNECIMENTO_MONOFASICO = "monofasico"
FORNECIMENTO_BIFASICO = "bifasico"
FORNECIMENTO_TRIFASICO = "trifasico"

# Custo de disponibilidade em kWh
DISPONIBILIDADE = {
    FORNECIMENTO_MONOFASICO: 30,
    FORNECIMENTO_BIFASICO: 50,
    FORNECIMENTO_TRIFASICO: 100,
}

PLATFORMS = ["sensor"]
