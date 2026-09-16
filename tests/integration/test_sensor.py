"""Entity identity, units, availability, and JSON-safe attributes."""

import json
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass

from custom_components.bitpanda.binary_sensor import (
    BitpandaEarnAvailableBinarySensor,
)
from custom_components.bitpanda.models import (
    AssetPosition,
    Completeness,
    Currency,
    EarnConfig,
    PortfolioSnapshot,
)
from custom_components.bitpanda.sensor import (
    ASSET_METRICS,
    EARN_ASSET_METRICS,
    PORTFOLIO_METRICS,
    BitpandaAssetSensor,
    BitpandaPortfolioSensor,
)


def test_asset_sensor_contract_and_json_safe_attributes() -> None:
    asset = AssetPosition(
        asset_id="asset-eth",
        currency_id="currency-eur",
        symbol="ETH",
        name="Ethereum",
        asset_type="CRYPTO",
        group="CRYPTOCOIN",
        isin=None,
        amount=Decimal("0.5"),
        available_amount=Decimal("0.5"),
        invested_amount=Decimal(1000),
        average_buy_price=Decimal(2000),
        current_value=Decimal(1500),
        current_price=Decimal(3000),
        total_return=Decimal(500),
        total_return_percent=Decimal(50),
        earn_configs=(
            EarnConfig(
                "config-eth",
                "asset-eth",
                Decimal("0.024"),
                "LOCKED",
                "STAKING_EARN",
                True,
                False,
            ),
        ),
    )
    snapshot = PortfolioSnapshot(
        datetime.now(UTC),
        Currency("currency-eur", "EUR", "Euro"),
        (asset,),
        Completeness.COMPLETE,
        total_current_value=Decimal(1500),
        total_invested_amount=Decimal(1000),
        total_return=Decimal(500),
        total_return_percent=Decimal(50),
    )
    coordinator = MagicMock()
    coordinator.data = snapshot
    coordinator.config_entry.entry_id = "entry-1"
    coordinator.last_update_success = True
    amount_metric = next(item for item in ASSET_METRICS if item.metric_id == "amount")
    entity = BitpandaAssetSensor(coordinator, asset, amount_metric)

    assert entity.unique_id == "entry-1:asset:asset-eth:amount"
    assert entity.native_value == Decimal("0.5")
    assert entity.native_unit_of_measurement == "ETH"
    assert entity.state_class is SensorStateClass.MEASUREMENT
    assert entity.extra_state_attributes["asset_symbol"] == "ETH"
    assert entity.extra_state_attributes["data_source"] == "bitpanda_public_api"
    assert entity.extra_state_attributes["earn_apr"] == 2.4
    assert entity.extra_state_attributes["earn_mode"] == "STAKING_EARN"
    assert entity.extra_state_attributes["earn_type"] == "LOCKED"
    json.dumps(entity.extra_state_attributes)

    earn_apr = BitpandaAssetSensor(coordinator, asset, EARN_ASSET_METRICS[0])
    assert earn_apr.native_value == Decimal("2.400")
    assert earn_apr.native_unit_of_measurement == "%"
    assert earn_apr.state_class is SensorStateClass.MEASUREMENT

    committed_metric = next(
        item for item in ASSET_METRICS if item.metric_id == "committed_amount"
    )
    committed = BitpandaAssetSensor(coordinator, asset, committed_metric)
    assert committed.native_value == Decimal(0)
    assert committed.native_unit_of_measurement == "ETH"

    earn_available = BitpandaEarnAvailableBinarySensor(coordinator, asset)
    assert earn_available.is_on is True
    assert earn_available.extra_state_attributes["earn_type"] == "LOCKED"
    json.dumps(earn_available.extra_state_attributes)

    current_value_metric = next(
        item for item in ASSET_METRICS if item.metric_id == "current_value"
    )
    current_value = BitpandaAssetSensor(coordinator, asset, current_value_metric)
    assert current_value.device_class is SensorDeviceClass.MONETARY
    assert current_value.state_class is SensorStateClass.TOTAL

    current_price_metric = next(
        item for item in ASSET_METRICS if item.metric_id == "current_price"
    )
    current_price = BitpandaAssetSensor(coordinator, asset, current_price_metric)
    assert current_price.device_class is SensorDeviceClass.MONETARY
    assert current_price.state_class is None

    portfolio_value_metric = next(
        item for item in PORTFOLIO_METRICS if item.metric_id == "current_value"
    )
    portfolio_value = BitpandaPortfolioSensor(
        coordinator,
        "portfolio",
        "account",
        portfolio_value_metric,
        portfolio_value_metric.name,
    )
    assert portfolio_value.device_class is SensorDeviceClass.MONETARY
    assert portfolio_value.state_class is SensorStateClass.TOTAL
    assert all(
        metric.state_class is SensorStateClass.TOTAL
        for metric in PORTFOLIO_METRICS
        if metric.monetary
    )
