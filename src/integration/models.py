"""Typed models for Bitpanda's new Public API."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum


class Completeness(StrEnum):
    """Snapshot availability without pretending partial data is complete."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class Currency:
    """Bitpanda fiat currency metadata."""

    currency_id: str
    symbol: str
    name: str


@dataclass(frozen=True, slots=True)
class AssetMetadata:
    """Bitpanda asset metadata."""

    asset_id: str
    symbol: str
    name: str
    asset_type: str
    group: str
    isin: str | None = None


@dataclass(frozen=True, slots=True)
class EarnConfig:
    """One Bitpanda Earn product configuration for an asset."""

    config_id: str
    asset_id: str
    annual_percentage_rate: Decimal
    earn_type: str
    mode: str
    enabled: bool
    sold_out: bool

    @property
    def available(self) -> bool:
        """Return whether Bitpanda currently offers this configuration."""
        return self.enabled and not self.sold_out


@dataclass(frozen=True, slots=True)
class AssetPosition:
    """One portfolio position, with accounting supplied by Bitpanda."""

    asset_id: str
    currency_id: str
    symbol: str
    name: str
    asset_type: str
    group: str
    isin: str | None
    amount: Decimal
    available_amount: Decimal | None
    invested_amount: Decimal | None
    average_buy_price: Decimal | None
    current_value: Decimal | None
    current_price: Decimal | None
    total_return: Decimal | None
    total_return_percent: Decimal | None
    earn_configs: tuple[EarnConfig, ...] = ()

    @property
    def committed_amount(self) -> Decimal | None:
        """Return the non-available portion without claiming why it is held."""
        if self.available_amount is None:
            return None
        return max(Decimal(0), self.amount - self.available_amount)

    @property
    def committed_percentage(self) -> Decimal | None:
        """Return the percentage of the total balance that is unavailable."""
        committed = self.committed_amount
        if committed is None or self.amount <= 0:
            return None
        return committed / self.amount * 100

    @property
    def earn_config(self) -> EarnConfig | None:
        """Return the unambiguous config; multiple choices need native detail."""
        return self.earn_configs[0] if len(self.earn_configs) == 1 else None

    @property
    def earn_apr_percentage(self) -> Decimal | None:
        """Convert the API's fractional APR to Home Assistant percent units."""
        config = self.earn_config
        return config.annual_percentage_rate * 100 if config else None

    @property
    def earn_available(self) -> bool:
        """Return whether any Earn configuration is enabled and not sold out."""
        return any(config.available for config in self.earn_configs)


@dataclass(frozen=True, slots=True)
class PortfolioSnapshot:
    """One coherent Bitpanda portfolio snapshot in the selected currency."""

    updated_at: datetime
    currency: Currency
    assets: tuple[AssetPosition, ...]
    completeness: Completeness
    errors: tuple[str, ...] = ()
    total_current_value: Decimal | None = None
    total_invested_amount: Decimal | None = None
    total_return: Decimal | None = None
    total_return_percent: Decimal | None = None
    earn_data_available: bool = True
