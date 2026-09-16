"""Privacy-conscious Bitpanda diagnostics."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_API_KEY
from .coordinator import BitpandaCoordinator


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry[BitpandaCoordinator],
) -> dict[str, Any]:
    """Return useful status without exposing the API key or balances."""
    del hass
    coordinator = entry.runtime_data
    data = coordinator.data
    return {
        "config": async_redact_data(dict(entry.data), {CONF_API_KEY}),
        "options": dict(entry.options),
        "snapshot": {
            "updated_at": data.updated_at.isoformat(),
            "currency": data.currency.symbol,
            "completeness": data.completeness,
            "asset_count": len(data.assets),
            "total_current_value_available": data.total_current_value is not None,
            "total_invested_amount_available": data.total_invested_amount is not None,
            "total_return_available": data.total_return is not None,
            "earn_data_available": data.earn_data_available,
            "earn_configured_asset_count": sum(
                bool(item.earn_configs) for item in data.assets
            ),
            "earn_available_asset_count": sum(
                item.earn_available for item in data.assets
            ),
            "errors": list(data.errors),
        },
        "assets": [
            {
                "asset_id": item.asset_id,
                "symbol": item.symbol,
                "type": item.asset_type,
                "group": item.group,
                "amount_available": True,
                "valuation_available": item.current_value is not None,
                "performance_available": item.total_return is not None,
                "committed_amount_available": item.committed_amount is not None,
                "earn_config_count": len(item.earn_configs),
                "earn_apr_available": item.earn_apr_percentage is not None,
                "earn_available": item.earn_available,
                "earn_mode": item.earn_config.mode if item.earn_config else None,
                "earn_type": item.earn_config.earn_type if item.earn_config else None,
            }
            for item in data.assets
        ],
        "recent_errors": list(coordinator.recent_errors),
    }
