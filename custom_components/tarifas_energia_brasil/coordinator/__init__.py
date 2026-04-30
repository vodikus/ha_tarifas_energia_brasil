"""DataUpdateCoordinator para a integração Tarifas de Energia Brasil."""

"""DataUpdateCoordinator package para a integração Tarifas de Energia Brasil."""

from .base import TarifasDeEnergiaBrasilCoordinator
from .data_processing import get_state_float, process_coordinator_data
from .error_handling import handle_coordinator_errors
from .listeners import register_update_listener

__all__ = [
    "TarifasDeEnergiaBrasilCoordinator",
    "get_state_float",
    "handle_coordinator_errors",
    "process_coordinator_data",
    "register_update_listener",
]
