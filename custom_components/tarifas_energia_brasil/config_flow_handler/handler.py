"""Backwards compatibility wrapper for config flow handler."""

from .config_flow import TarifasDeEnergiaBrasilConfigFlowHandler
from .options_flow import TarifasDeEnergiaBrasilOptionsFlowHandler

__all__ = [
    "TarifasDeEnergiaBrasilConfigFlowHandler",
    "TarifasDeEnergiaBrasilOptionsFlowHandler",
]
