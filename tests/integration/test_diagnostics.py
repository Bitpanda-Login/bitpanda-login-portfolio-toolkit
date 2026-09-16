"""Diagnostics expose capability without balances or API secrets."""

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

from custom_components.bitpanda.const import CONF_API_KEY
from custom_components.bitpanda.diagnostics import async_get_config_entry_diagnostics
from custom_components.bitpanda.models import (
    AssetPosition,
    Completeness,
    Currency,
    EarnConfig,
    PortfolioSnapshot,
)


async def test_earn_diagnostics_are_useful_and_privacy_preserving() -> None:
    config = EarnConfig(
        "config-atom",
        "asset-atom",
        Decimal("0.1486"),
        "FLEXIBLE",
        "STAKING_EARN",
        True,
        False,
    )
    asset = AssetPosition(
        asset_id="asset-atom",
        currency_id="currency-eur",
        symbol="ATOM",
        name="Cosmos",
        asset_type="CRYPTO",
        group="CRYPTOCOIN",
        isin=None,
        amount=Decimal(10),
        available_amount=Decimal(1),
        invested_amount=Decimal(50),
        average_buy_price=Decimal(5),
        current_value=Decimal(100),
        current_price=Decimal(10),
        total_return=Decimal(50),
        total_return_percent=Decimal(100),
        earn_configs=(config,),
    )
    snapshot = PortfolioSnapshot(
        datetime.now(UTC),
        Currency("currency-eur", "EUR", "Euro"),
        (asset,),
        Completeness.COMPLETE,
        total_current_value=Decimal(100),
        total_invested_amount=Decimal(50),
        total_return=Decimal(50),
        total_return_percent=Decimal(100),
    )
    entry = SimpleNamespace(
        data={CONF_API_KEY: "never-export-this"},
        options={},
        runtime_data=SimpleNamespace(data=snapshot, recent_errors=[]),
    )

    diagnostics = await async_get_config_entry_diagnostics(None, entry)

    assert diagnostics["config"][CONF_API_KEY] == "**REDACTED**"
    assert diagnostics["snapshot"]["earn_configured_asset_count"] == 1
    assert diagnostics["snapshot"]["earn_available_asset_count"] == 1
    assert diagnostics["assets"][0]["earn_mode"] == "STAKING_EARN"
    assert diagnostics["assets"][0]["earn_apr_available"] is True
    assert "never-export-this" not in str(diagnostics)
    assert "amount" not in diagnostics["assets"][0]
    assert "available_amount" not in diagnostics["assets"][0]
    assert "current_value" not in diagnostics["assets"][0]
