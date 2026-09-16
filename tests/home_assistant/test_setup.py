"""End-to-end custom integration setup with the Public API mocked."""

from dataclasses import replace
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bitpanda.api import BitpandaApiError, BitpandaClient
from custom_components.bitpanda.const import CONF_API_KEY, DOMAIN
from custom_components.bitpanda.models import (
    AssetMetadata,
    AssetPosition,
    Currency,
    EarnConfig,
)


async def test_setup_creates_portfolio_and_asset_entities(hass) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Bitpanda Portfolio",
        data={CONF_API_KEY: "secret"},
        unique_id="fingerprint",
    )
    entry.add_to_hass(hass)
    raw = {
        "assetId": "asset-eth",
        "currencyId": "currency-eur",
        "balance": {"value": "0.5"},
        "availableBalance": {"value": "0.5"},
        "investedAmount": {"value": "1000"},
        "averageBuyPrice": {"value": "2000"},
        "currencyBalance": {"value": "1500"},
        "totalReturn": {"value": "500"},
        "totalReturnPercent": "50",
    }
    with (
        patch.object(
            BitpandaClient,
            "async_currency",
            AsyncMock(return_value=Currency("currency-eur", "EUR", "Euro")),
        ),
        patch.object(
            BitpandaClient,
            "async_currencies",
            AsyncMock(return_value=(Currency("currency-eur", "EUR", "Euro"),)),
        ),
        patch.object(BitpandaClient, "async_portfolio", AsyncMock(return_value=[raw])),
        patch.object(
            BitpandaClient,
            "async_assets",
            AsyncMock(
                return_value={
                    "asset-eth": AssetMetadata(
                        "asset-eth",
                        "ETH",
                        "Ethereum",
                        "CRYPTO",
                        "CRYPTOCOIN",
                    )
                }
            ),
        ),
        patch.object(
            BitpandaClient,
            "async_earn_configs",
            AsyncMock(
                return_value={
                    "asset-eth": (
                        EarnConfig(
                            "config-eth",
                            "asset-eth",
                            Decimal("0.024"),
                            "LOCKED",
                            "STAKING_EARN",
                            True,
                            False,
                        ),
                    )
                }
            ),
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    states = [
        state
        for state in hass.states.async_all("sensor")
        if state.attributes.get("integration_domain") == DOMAIN
    ]
    assert len(states) == 16
    assert any(
        state.attributes.get("metric_id") == "api_status" and state.state == "complete"
        for state in states
    )
    amount = next(
        state
        for state in states
        if state.attributes.get("asset_symbol") == "ETH"
        and state.attributes.get("metric_id") == "amount"
    )
    assert amount.state == "0.5"
    assert amount.attributes["unit_of_measurement"] == "ETH"
    portfolio_value = next(
        state
        for state in states
        if state.attributes.get("resource_type") == "portfolio"
        and state.attributes.get("metric_id") == "current_value"
    )
    assert portfolio_value.attributes["device_class"] == "monetary"
    assert portfolio_value.attributes["state_class"] == "total"
    earn_apr = next(
        state
        for state in states
        if state.attributes.get("asset_symbol") == "ETH"
        and state.attributes.get("metric_id") == "earn_apr"
    )
    assert Decimal(earn_apr.state) == Decimal("2.4")
    assert earn_apr.attributes["unit_of_measurement"] == "%"
    earn_available = next(
        state
        for state in hass.states.async_all("binary_sensor")
        if state.attributes.get("asset_symbol") == "ETH"
    )
    assert earn_available.state == "on"

    coordinator = entry.runtime_data
    atom = AssetPosition(
        asset_id="asset-atom",
        currency_id="currency-eur",
        symbol="ATOM",
        name="Cosmos",
        asset_type="CRYPTO",
        group="CRYPTOCOIN",
        isin=None,
        amount=Decimal("2"),
        available_amount=Decimal("2"),
        invested_amount=Decimal("10"),
        average_buy_price=Decimal("5"),
        current_value=Decimal("12"),
        current_price=Decimal("6"),
        total_return=Decimal("2"),
        total_return_percent=Decimal("20"),
        earn_configs=(
            EarnConfig(
                "config-atom",
                "asset-atom",
                Decimal("0.1486"),
                "FLEXIBLE",
                "STAKING_EARN",
                True,
                False,
            ),
        ),
    )
    coordinator.async_set_updated_data(
        replace(coordinator.data, assets=(*coordinator.data.assets, atom))
    )
    await hass.async_block_till_done()

    discovered = [
        state
        for state in hass.states.async_all("sensor")
        if state.attributes.get("asset_symbol") == "ATOM"
    ]
    assert len(discovered) == 11
    discovered_binary = [
        state
        for state in hass.states.async_all("binary_sensor")
        if state.attributes.get("asset_symbol") == "ATOM"
    ]
    assert len(discovered_binary) == 1
    assert discovered_binary[0].state == "on"


async def test_earn_failure_keeps_portfolio_available_and_marks_partial(hass) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Bitpanda Portfolio",
        data={CONF_API_KEY: "secret"},
        unique_id="earn-failure",
    )
    entry.add_to_hass(hass)
    raw = {
        "assetId": "asset-eth",
        "currencyId": "currency-eur",
        "balance": {"value": "0.5"},
        "availableBalance": {"value": "0.4"},
        "investedAmount": {"value": "1000"},
        "averageBuyPrice": {"value": "2000"},
        "currencyBalance": {"value": "1500"},
        "totalReturn": {"value": "500"},
        "totalReturnPercent": "50",
    }
    with (
        patch.object(
            BitpandaClient,
            "async_currency",
            AsyncMock(return_value=Currency("currency-eur", "EUR", "Euro")),
        ),
        patch.object(
            BitpandaClient,
            "async_currencies",
            AsyncMock(return_value=(Currency("currency-eur", "EUR", "Euro"),)),
        ),
        patch.object(BitpandaClient, "async_portfolio", AsyncMock(return_value=[raw])),
        patch.object(
            BitpandaClient,
            "async_assets",
            AsyncMock(
                return_value={
                    "asset-eth": AssetMetadata(
                        "asset-eth",
                        "ETH",
                        "Ethereum",
                        "CRYPTO",
                        "CRYPTOCOIN",
                    )
                }
            ),
        ),
        patch.object(
            BitpandaClient,
            "async_earn_configs",
            AsyncMock(side_effect=BitpandaApiError(503, "earn_unavailable")),
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    status = next(
        state
        for state in hass.states.async_all("sensor")
        if state.attributes.get("metric_id") == "api_status"
    )
    assert status.state == "partial"
    assert status.attributes["errors"] == ["earn_configs:earn_unavailable"]
    amount = next(
        state
        for state in hass.states.async_all("sensor")
        if state.attributes.get("asset_symbol") == "ETH"
        and state.attributes.get("metric_id") == "amount"
    )
    assert amount.state == "0.5"
    assert not any(
        state.attributes.get("metric_id") == "earn_apr"
        for state in hass.states.async_all("sensor")
    )
    earn_entities = hass.states.async_all("binary_sensor")
    assert len(earn_entities) == 1
    assert earn_entities[0].state == "unavailable"
