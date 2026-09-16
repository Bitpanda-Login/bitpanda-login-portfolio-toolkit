"""Home Assistant setup for Bitpanda's read-only Public API."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import BitpandaClient
from .const import (
    CONF_API_KEY,
    CONF_INCLUDE_ZERO_BALANCES,
    CONF_SCAN_INTERVAL,
    DEFAULT_INCLUDE_ZERO_BALANCES,
    DEFAULT_SCAN_INTERVAL,
    DISPLAY_CURRENCY,
)
from .coordinator import BitpandaCoordinator

PLATFORMS = ("sensor", "binary_sensor")


async def async_setup_entry(hass: Any, entry: Any) -> bool:
    """Set up one Bitpanda account."""
    client = BitpandaClient(
        async_get_clientsession(hass),
        entry.data[CONF_API_KEY],
    )
    coordinator = BitpandaCoordinator(
        hass,
        entry,
        client,
        DISPLAY_CURRENCY,
        entry.options.get(CONF_INCLUDE_ZERO_BALANCES, DEFAULT_INCLUDE_ZERO_BALANCES),
        timedelta(seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)),
    )
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: Any, entry: Any) -> bool:
    """Unload the config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload_entry(hass: Any, entry: Any) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
