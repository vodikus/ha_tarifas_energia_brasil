"""Error handling and recovery strategies for the coordinator.

This module provides utilities for handling errors that occur during
data updates, including retry logic, circuit breaker patterns, and
graceful degradation strategies.
"""

import logging

from homeassistant.helpers.update_coordinator import UpdateFailed

_LOGGER = logging.getLogger(__name__)


def handle_coordinator_errors(func):
    """Decorator for graceful degradation and error mapping during updates."""

    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as err:
            _LOGGER.exception("Unexpected error fetching data: %s", err)
            raise UpdateFailed(f"Erro na atualização dos dados: {err}") from err

    return wrapper
