"""Event listeners and callbacks for coordinator state changes.

This module provides utilities for managing entity callbacks and event
listeners that respond to coordinator state changes.
"""

import logging

_LOGGER = logging.getLogger(__name__)


def register_update_listener(coordinator, listener_func):
    """Register a custom listener to the coordinator."""
    return coordinator.async_add_listener(listener_func)
