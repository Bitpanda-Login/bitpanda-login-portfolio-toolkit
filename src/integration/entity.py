"""Shared Bitpanda entity identity and attribute contracts."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_CONFIG_ENTRY_ID,
    ATTR_INTEGRATION_DOMAIN,
    ATTR_METRIC_ID,
    ATTR_RESOURCE_ID,
    ATTR_RESOURCE_TYPE,
    DOMAIN,
)
from .coordinator import BitpandaCoordinator
from .models import AssetPosition


class BitpandaEntity(CoordinatorEntity[BitpandaCoordinator]):
    """Base entity with a stable, attribute-based public contract."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BitpandaCoordinator,
        resource_type: str,
        resource_id: str,
        metric_id: str,
    ) -> None:
        super().__init__(coordinator)
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.metric_id = metric_id
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}:{resource_type}:"
            f"{resource_id}:{metric_id}"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name="Bitpanda Portfolio",
            manufacturer="Bitpanda",
            model="Public API portfolio",
            configuration_url="https://web.bitpanda.com/portfolio",
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            ATTR_INTEGRATION_DOMAIN: DOMAIN,
            ATTR_CONFIG_ENTRY_ID: self.coordinator.config_entry.entry_id,
            ATTR_RESOURCE_TYPE: self.resource_type,
            ATTR_RESOURCE_ID: self.resource_id,
            ATTR_METRIC_ID: self.metric_id,
            "currency": self.coordinator.data.currency.symbol,
            "completeness": self.coordinator.data.completeness,
            "errors": list(self.coordinator.data.errors),
        }


def asset_earn_attributes(position: AssetPosition | None) -> dict[str, Any]:
    """Return JSON-safe Earn configuration attributes for one asset."""
    configs = position.earn_configs if position else ()
    config = position.earn_config if position else None
    return {
        "earn_config_count": len(configs),
        "earn_config_id": config.config_id if config else None,
        "earn_mode": config.mode if config else None,
        "earn_type": config.earn_type if config else None,
        "earn_enabled": config.enabled if config else None,
        "earn_sold_out": config.sold_out if config else None,
        "earn_apr": (
            float(position.earn_apr_percentage)
            if position and position.earn_apr_percentage is not None
            else None
        ),
        "earn_apr_unavailable_reason": (
            "multiple_earn_configs" if len(configs) > 1 else None
        ),
        "earn_configs": [
            {
                "config_id": item.config_id,
                "apr": float(item.annual_percentage_rate * 100),
                "mode": item.mode,
                "type": item.earn_type,
                "enabled": item.enabled,
                "sold_out": item.sold_out,
                "available": item.available,
            }
            for item in configs
        ],
    }
