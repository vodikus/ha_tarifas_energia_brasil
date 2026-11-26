"""Constantes para a integração Tarifas de Energia Brasil."""

DOMAIN = "tarifas_energia_brasil"

CONF_CONCESSIONARIA = "concessionaria"

CONF_POLLING_MODE = "polling_mode"
POLLING_AUTOMATIC = "automatic"
POLLING_DAILY = "daily"
POLLING_EVERY_2_DAYS = "every_2_days"
POLLING_WEEKLY = "weekly"
POLLING_MODES = [POLLING_AUTOMATIC, POLLING_DAILY, POLLING_EVERY_2_DAYS, POLLING_WEEKLY]

# Intervalos fixos em dias; "automatic" usa dat_fim_vigencia (comportamento anterior).
POLLING_FIXED_DAYS = {
    POLLING_DAILY: 1,
    POLLING_EVERY_2_DAYS: 2,
    POLLING_WEEKLY: 7,
}

# Estados de atualização expostos no sensor de diagnóstico.
STATUS_ONLINE = "online"
STATUS_CACHE = "cache"
STATUS_SEM_DADOS = "sem_dados"

# A conectividade e a atualidade do conteúdo são diagnósticos independentes.
DATA_CURRENT = "atual"
DATA_EXPIRED = "tarifa_expirada"
DATA_FUTURE = "tarifa_futura"
DATA_FLAG_STALE = "bandeira_desatualizada"
DATA_INCOMPLETE = "dados_incompletos"
DATA_UNAVAILABLE = "sem_dados"

CLOUDFLARE_BASE_URL = (
    "https://ha-tarifas-energia-brasil-service.vodikus.workers.dev/api/v1"
)

SERVICE_ATUALIZAR = "atualizar_tarifas"
