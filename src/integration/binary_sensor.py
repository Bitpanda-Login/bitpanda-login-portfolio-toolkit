"""Bitpanda Earn availability binary sensors."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    ATTR_ASSET_ID,
    ATTR_ASSET_SYMBOL,
    RESOURCE_ASSET,
)
from .coordinator import BitpandaCoordinator
from .entity import BitpandaEntity, asset_earn_attributes
from .models import AssetPosition


class BitpandaEarnAvailableBinarySensor(BitpandaEntity, BinarySensorEntity):
    """Whether Bitpanda currently offers an Earn config for one holding."""

    _attr_icon = "mdi:finance"

    def __init__(self, coordinator: BitpandaCoordinator, asset: AssetPosition) -> None:
        self.asset_id = asset.asset_id
        self.symbol = asset.symbol
        super().__init__(
            coordinator,
            RESOURCE_ASSET,
            asset.asset_id,
            "earn_available",
        )
        self._attr_name = f"{asset.symbol} Earn available"

    def _position(self) -> AssetPosition | None:
        return next(
            (
                item
                for item in self.coordinator.data.assets
                if item.asset_id == self.asset_id
            ),
            None,
        )

    @property
    def is_on(self) -> bool:
        position = self._position()
        return position.earn_available if position else False

    @property
    def available(self) -> bool:
        return (
            super().available
            and self.coordinator.data.earn_data_available
            and self._position() is not None
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        position = self._position()
        return {
            **super().extra_state_attributes,
            ATTR_ASSET_ID: self.asset_id,
            ATTR_ASSET_SYMBOL: position.symbol if position else self.symbol,
            **asset_earn_attributes(position),
        }


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[BitpandaCoordinator],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add availability entities for dynamically discovered holdings."""
    del hass
    coordinator = entry.runtime_data
    known_assets: set[str] = set()

    @callback
    def async_add_discovered_assets() -> None:
        new_assets = [
            asset
            for asset in coordinator.data.assets
            if asset.asset_id not in known_assets
        ]
        if not new_assets:
            return
        known_assets.update(asset.asset_id for asset in new_assets)
        async_add_entities(
            BitpandaEarnAvailableBinarySensor(coordinator, asset)
            for asset in new_assets
        )

    async_add_discovered_assets()
    entry.async_on_unload(coordinator.async_add_listener(async_add_discovered_assets))
