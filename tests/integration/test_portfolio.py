"""Portfolio normalization using Bitpanda-provided accounting fields."""

from decimal import Decimal

from custom_components.bitpanda.models import (
    AssetMetadata,
    Completeness,
    Currency,
    EarnConfig,
)
from custom_components.bitpanda.portfolio import build_snapshot

EUR = Currency("currency-eur", "EUR", "Euro")
ASSETS = {
    "asset-eth": AssetMetadata("asset-eth", "ETH", "Ethereum", "CRYPTO", "CRYPTOCOIN"),
    "asset-atom": AssetMetadata("asset-atom", "ATOM", "Cosmos", "CRYPTO", "CRYPTOCOIN"),
    "currency-eur": AssetMetadata("currency-eur", "EUR", "Euro", "FIAT", "FIAT"),
}


def position(
    asset_id: str,
    balance: str,
    invested: str | None,
    current: str | None,
    total_return: str | None,
    return_percent: str | None,
) -> dict:
    def money(value: str | None):
        return {"value": value} if value is not None else None

    amount = Decimal(balance)
    average = Decimal(invested) / amount if invested is not None and amount else None
    return {
        "assetId": asset_id,
        "currencyId": "currency-eur",
        "balance": money(balance),
        "availableBalance": money(balance),
        "investedAmount": money(invested),
        "averageBuyPrice": money(str(average) if average is not None else None),
        "currencyBalance": money(current),
        "totalReturn": money(total_return),
        "totalReturnPercent": return_percent,
    }


def test_authoritative_values_and_portfolio_totals() -> None:
    snapshot = build_snapshot(
        [
            position("asset-eth", "0.063", "180", "105", "-75", "-41.6667"),
            position("asset-atom", "26", "90", "30", "-60", "-66.6667"),
        ],
        ASSETS,
        EUR,
        False,
    )

    assert snapshot.completeness is Completeness.COMPLETE
    assert snapshot.total_current_value == Decimal(135)
    assert snapshot.total_invested_amount == Decimal(270)
    assert snapshot.total_return == Decimal(-135)
    assert snapshot.total_return_percent == Decimal(-50)
    eth = next(item for item in snapshot.assets if item.symbol == "ETH")
    assert eth.amount == Decimal("0.063")
    assert eth.average_buy_price == Decimal(180) / Decimal("0.063")
    assert eth.current_price == Decimal(105) / Decimal("0.063")


def test_zero_balances_are_optional() -> None:
    raw = [position("asset-eth", "0", None, "0", "0", None)]
    assert build_snapshot(raw, ASSETS, EUR, False).assets == ()
    shown = build_snapshot(raw, ASSETS, EUR, True)
    assert len(shown.assets) == 1
    assert shown.assets[0].current_price is None


def test_missing_bitpanda_performance_is_partial_not_guessed() -> None:
    snapshot = build_snapshot(
        [position("asset-eth", "1", None, "100", None, None)],
        ASSETS,
        EUR,
        False,
    )
    assert snapshot.completeness is Completeness.PARTIAL
    assert snapshot.total_current_value == Decimal(100)
    assert snapshot.total_invested_amount is None
    assert snapshot.total_return is None
    assert snapshot.total_return_percent is None
    assert snapshot.errors == ("asset-eth:performance_unavailable",)


def test_missing_metadata_is_explicit_and_does_not_hide_balance() -> None:
    snapshot = build_snapshot(
        [position("asset-eth", "1", "50", "100", "50", "100")],
        {},
        EUR,
        False,
    )
    assert snapshot.assets[0].amount == Decimal(1)
    assert snapshot.completeness is Completeness.PARTIAL
    assert "asset-eth:metadata_unavailable" in snapshot.errors


def test_display_currency_cash_is_in_value_but_not_performance_totals() -> None:
    cash = {
        "currencyId": "currency-eur",
        "balance": {"value": "25"},
        "availableBalance": {"value": "20"},
    }
    snapshot = build_snapshot(
        [position("asset-eth", "1", "50", "100", "50", "100"), cash],
        ASSETS,
        EUR,
        False,
    )

    assert snapshot.completeness is Completeness.COMPLETE
    assert snapshot.total_current_value == Decimal(125)
    assert snapshot.total_invested_amount == Decimal(50)
    assert snapshot.total_return == Decimal(50)
    assert snapshot.total_return_percent == Decimal(100)
    eur = next(item for item in snapshot.assets if item.symbol == "EUR")
    assert eur.amount == Decimal(25)
    assert eur.available_amount == Decimal(20)
    assert eur.current_value == Decimal(25)
    assert eur.invested_amount is None
    assert eur.total_return is None


def test_committed_balance_and_earn_configuration_are_explicit() -> None:
    raw = position("asset-atom", "10", "50", "100", "50", "100")
    raw["availableBalance"] = {"value": "1"}
    config = EarnConfig(
        "config-atom",
        "asset-atom",
        Decimal("0.1486"),
        "FLEXIBLE",
        "STAKING_EARN",
        True,
        False,
    )

    snapshot = build_snapshot(
        [raw],
        ASSETS,
        EUR,
        False,
        {"asset-atom": (config,)},
    )
    atom = snapshot.assets[0]

    assert snapshot.earn_data_available is True
    assert atom.committed_amount == Decimal(9)
    assert atom.committed_percentage == Decimal(90)
    assert atom.earn_apr_percentage == Decimal("14.8600")
    assert atom.earn_available is True
    assert atom.earn_config is config
