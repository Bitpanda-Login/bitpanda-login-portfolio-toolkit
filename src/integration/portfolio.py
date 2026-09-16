"""Normalize authoritative Bitpanda portfolio fields for Home Assistant."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from .models import (
    AssetMetadata,
    AssetPosition,
    Completeness,
    Currency,
    EarnConfig,
    PortfolioSnapshot,
)


def build_snapshot(
    raw_positions: list[dict[str, Any]],
    assets: dict[str, AssetMetadata],
    currency: Currency,
    include_zero_balances: bool,
    earn_configs: dict[str, tuple[EarnConfig, ...]] | None = None,
) -> PortfolioSnapshot:
    """Build a portfolio without reimplementing Bitpanda's accounting."""
    positions: list[AssetPosition] = []
    errors: list[str] = []
    for raw in raw_positions:
        asset_id = raw.get("assetId")
        position_currency_id = raw.get("currencyId")
        is_fiat = not isinstance(asset_id, str) and isinstance(
            position_currency_id, str
        )
        resource_id = position_currency_id if is_fiat else asset_id
        if not isinstance(resource_id, str):
            errors.append("position_missing_resource_id")
            continue
        metadata = assets.get(resource_id)
        if metadata is None:
            errors.append(f"{resource_id}:metadata_unavailable")
            metadata = AssetMetadata(
                resource_id, resource_id[:8], resource_id, "unknown", "unknown"
            )
        amount = _money(raw.get("balance"))
        if amount is None:
            errors.append(f"{resource_id}:balance_unavailable")
            continue
        if amount == 0 and not include_zero_balances:
            continue
        current_value = (
            amount
            if is_fiat and position_currency_id == currency.currency_id
            else _money(raw.get("currencyBalance"))
        )
        invested = _money(raw.get("investedAmount"))
        average = _money(raw.get("averageBuyPrice"))
        total_return = _money(raw.get("totalReturn"))
        return_pct = _decimal(raw.get("totalReturnPercent"))
        if current_value is None:
            errors.append(f"{resource_id}:current_value_unavailable")
        if (
            not is_fiat
            and amount > 0
            and any(
                item is None for item in (invested, average, total_return, return_pct)
            )
        ):
            errors.append(f"{resource_id}:performance_unavailable")
        positions.append(
            AssetPosition(
                asset_id=resource_id,
                currency_id=str(position_currency_id or currency.currency_id),
                symbol=metadata.symbol,
                name=metadata.name,
                asset_type=metadata.asset_type,
                group=metadata.group,
                isin=metadata.isin,
                amount=amount,
                available_amount=_money(raw.get("availableBalance")),
                invested_amount=invested,
                average_buy_price=average,
                current_value=current_value,
                current_price=(
                    current_value / amount
                    if current_value is not None and amount
                    else None
                ),
                total_return=total_return,
                total_return_percent=return_pct,
                earn_configs=(earn_configs or {}).get(resource_id, ()),
            )
        )

    positions.sort(
        key=lambda item: (
            -(item.current_value or Decimal(0)),
            item.symbol,
            item.asset_id,
        )
    )
    total_value = _complete_sum(item.current_value for item in positions)
    performance_positions = [
        item for item in positions if item.asset_type.upper() != "FIAT"
    ]
    total_invested = _complete_sum(
        item.invested_amount for item in performance_positions
    )
    total_return = _complete_sum(item.total_return for item in performance_positions)
    total_return_pct = (
        total_return / total_invested * 100
        if total_return is not None and total_invested not in (None, 0)
        else None
    )
    return PortfolioSnapshot(
        updated_at=datetime.now(UTC),
        currency=currency,
        assets=tuple(positions),
        completeness=Completeness.PARTIAL if errors else Completeness.COMPLETE,
        errors=tuple(errors),
        total_current_value=total_value,
        total_invested_amount=total_invested,
        total_return=total_return,
        total_return_percent=total_return_pct,
        earn_data_available=earn_configs is not None,
    )


def _money(value: Any) -> Decimal | None:
    return _decimal(value.get("value")) if isinstance(value, dict) else None


def _decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return result if result.is_finite() else None


def _complete_sum(values: Any) -> Decimal | None:
    result = Decimal(0)
    for value in values:
        if value is None:
            return None
        result += value
    return result
