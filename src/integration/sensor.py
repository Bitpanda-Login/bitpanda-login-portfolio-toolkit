"""Bitpanda portfolio and per-asset sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    ATTR_ASSET_ID,
    ATTR_ASSET_SYMBOL,
    RESOURCE_ASSET,
    RESOURCE_PORTFOLIO,
)
from .coordinator import BitpandaCoordinator
from .entity import BitpandaEntity, asset_earn_attributes
from .models import AssetPosition


@dataclass(frozen=True, slots=True)
class Metric:
    """One entity metric over a snapshot or asset position."""

    metric_id: str
    name: str
    value: Callable[[Any], Any]
    precision: int
    monetary: bool = False
    percentage: bool = False
    state_class: SensorStateClass | None = SensorStateClass.MEASUREMENT


PORTFOLIO_METRICS = (
    Metric(
        "current_value",
        "Current value",
        lambda item: item.total_current_value,
        2,
        monetary=True,
        state_class=SensorStateClass.TOTAL,
    ),
    Metric(
        "invested_amount",
        "Invested amount",
        lambda item: item.total_invested_amount,
        2,
        monetary=True,
        state_class=SensorStateClass.TOTAL,
    ),
    Metric(
        "total_return",
        "Total return",
        lambda item: item.total_return,
        2,
        monetary=True,
        state_class=SensorStateClass.TOTAL,
    ),
    Metric(
        "total_return_percent",
        "Total return percent",
        lambda item: item.total_return_percent,
        2,
        percentage=True,
    ),
)

ASSET_METRICS = (
    Metric("amount", "Amount", lambda item: item.amount, 8),
    Metric(
        "available_amount", "Available amount", lambda item: item.available_amount, 8
    ),
    Metric(
        "committed_amount", "Committed amount", lambda item: item.committed_amount, 8
    ),
    Metric(
        "committed_percentage",
        "Committed percentage",
        lambda item: item.committed_percentage,
        2,
        percentage=True,
    ),
    Metric(
        "invested_amount",
        "Invested amount",
        lambda item: item.invested_amount,
        2,
        monetary=True,
        state_class=SensorStateClass.TOTAL,
    ),
    Metric(
        "average_buy_price",
        "Average buy price",
        lambda item: item.average_buy_price,
        6,
        monetary=True,
        state_class=None,
    ),
    Metric(
        "current_value",
        "Current value",
        lambda item: item.current_value,
        2,
        monetary=True,
        state_class=SensorStateClass.TOTAL,
    ),
    Metric(
        "current_price",
        "Current price",
        lambda item: item.current_price,
        6,
        monetary=True,
        state_class=None,
    ),
    Metric(
        "total_return",
        "Total return",
        lambda item: item.total_return,
        2,
        monetary=True,
        state_class=SensorStateClass.TOTAL,
    ),
    Metric(
        "total_return_percent",
        "Total return percent",
        lambda item: item.total_return_percent,
        2,
        percentage=True,
    ),
)

EARN_ASSET_METRICS = (
    Metric(
        "earn_apr",
        "Earn APR",
        lambda item: item.earn_apr_percentage,
        2,
        percentage=True,
    ),
)


class BitpandaMetricSensor(BitpandaEntity, SensorEntity):
    """Common numeric sensor behavior."""

    def __init__(
        self,
        coordinator: BitpandaCoordinator,
        resource_type: str,
        resource_id: str,
        metric: Metric,
        name: str,
    ) -> None:
        self.metric = metric
        super().__init__(coordinator, resource_type, resource_id, metric.metric_id)
        self._attr_name = name
        self._attr_suggested_display_precision = metric.precision
        self._attr_state_class = metric.state_class
        self._attr_device_class = (
            SensorDeviceClass.MONETARY if metric.monetary else None
        )

    @property
    def native_unit_of_measurement(self) -> str | None:
        if self.metric.monetary:
            return self.coordinator.data.currency.symbol
        if self.metric.percentage:
            return PERCENTAGE
        return None

    @property
    def available(self) -> bool:
        return super().available and self.native_value is not None


class BitpandaStatusSensor(BitpandaEntity, SensorEntity):
    """Portfolio completeness and current/recent error reporting."""

    _attr_name = "API status"

    def __init__(self, coordinator: BitpandaCoordinator) -> None:
        metric = Metric("api_status", "API status", lambda item: item.completeness, 0)
        super().__init__(coordinator, RESOURCE_PORTFOLIO, "account", metric.metric_id)

    @property
    def native_value(self) -> str:
        return self.coordinator.data.completeness

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            **super().extra_state_attributes,
            "recent_errors": list(self.coordinator.recent_errors),
        }


class BitpandaPortfolioSensor(BitpandaMetricSensor):
    """Portfolio aggregate directly over Bitpanda's authoritative fields."""

    @property
    def native_value(self) -> Decimal | None:
        return self.metric.value(self.coordinator.data)


class BitpandaAssetSensor(BitpandaMetricSensor):
    """One metric for a stable Bitpanda asset UUID."""

    def __init__(
        self,
        coordinator: BitpandaCoordinator,
        asset: AssetPosition,
        metric: Metric,
    ) -> None:
        self.asset_id = asset.asset_id
        self.symbol = asset.symbol
        super().__init__(
            coordinator,
            RESOURCE_ASSET,
            asset.asset_id,
            metric,
            f"{asset.symbol} {metric.name}",
        )

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
    def native_value(self) -> Decimal | None:
        position = self._position()
        return self.metric.value(position) if position else None

    @property
    def native_unit_of_measurement(self) -> str | None:
        if self.metric.metric_id in (
            "amount",
            "available_amount",
            "committed_amount",
        ):
            return self.symbol
        return super().native_unit_of_measurement

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs = super().extra_state_attributes
        position = self._position()
        attrs.update(
            {
                ATTR_ASSET_ID: self.asset_id,
                ATTR_ASSET_SYMBOL: position.symbol if position else self.symbol,
                "asset_name": position.name if position else None,
                "asset_type": position.asset_type if position else None,
                "asset_group": position.group if position else None,
                "isin": position.isin if position else None,
                "currency_id": position.currency_id if position else None,
                "data_source": "bitpanda_public_api",
                **asset_earn_attributes(position),
            }
        )
        return attrs


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[BitpandaCoordinator],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add aggregates and dynamically discovered Bitpanda assets."""
    del hass
    coordinator = entry.runtime_data
    async_add_entities(
        [
            BitpandaStatusSensor(coordinator),
            *(
                BitpandaPortfolioSensor(
                    coordinator,
                    RESOURCE_PORTFOLIO,
                    "account",
                    metric,
                    metric.name,
                )
                for metric in PORTFOLIO_METRICS
            ),
        ]
    )
    known_metrics: set[tuple[str, str]] = set()

    @callback
    def async_add_discovered_assets() -> None:
        entities = []
        for asset in coordinator.data.assets:
            metrics = (
                (*ASSET_METRICS, *EARN_ASSET_METRICS)
                if asset.earn_configs
                else ASSET_METRICS
            )
            for metric in metrics:
                identity = (asset.asset_id, metric.metric_id)
                if identity in known_metrics:
                    continue
                known_metrics.add(identity)
                entities.append(BitpandaAssetSensor(coordinator, asset, metric))
        if not entities:
            return
        async_add_entities(entities)

    async_add_discovered_assets()
    entry.async_on_unload(coordinator.async_add_listener(async_add_discovered_assets))
