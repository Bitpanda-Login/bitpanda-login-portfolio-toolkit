"""Bitpanda portfolio coordinator."""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BitpandaApiError, BitpandaAuthenticationError, BitpandaClient
from .const import DOMAIN
from .models import AssetMetadata, Completeness, Currency, PortfolioSnapshot
from .portfolio import build_snapshot

_LOGGER = logging.getLogger(__name__)


class BitpandaCoordinator(DataUpdateCoordinator[PortfolioSnapshot]):
    """Fetch one authoritative portfolio snapshot per interval."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        client: BitpandaClient,
        currency_symbol: str,
        include_zero_balances: bool,
        update_interval: timedelta,
    ) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name=f"{DOMAIN}_{config_entry.entry_id}",
            update_interval=update_interval,
        )
        self.config_entry = config_entry
        self.client = client
        self.currency_symbol = currency_symbol
        self.include_zero_balances = include_zero_balances
        self.currency: Currency | None = None
        self.currencies: dict[str, Currency] = {}
        self.recent_errors: list[str] = []

    async def _async_update_data(self) -> PortfolioSnapshot:
        """Fetch balances/performance first; metadata failure remains partial."""
        try:
            if self.currency is None:
                self.currency = await self.client.async_currency(self.currency_symbol)
                self.currencies = {
                    currency.currency_id: currency
                    for currency in await self.client.async_currencies()
                }
            raw = await self.client.async_portfolio(self.currency.currency_id)
        except BitpandaAuthenticationError as err:
            raise ConfigEntryAuthFailed("Bitpanda API key is invalid") from err
        except BitpandaApiError as err:
            self._remember(err.code)
            raise UpdateFailed(f"Bitpanda API update failed: {err.code}") from err

        asset_ids = {
            item["assetId"] for item in raw if isinstance(item.get("assetId"), str)
        }
        metadata_error: str | None = None
        try:
            assets = await self.client.async_assets(asset_ids)
        except BitpandaAuthenticationError as err:
            raise ConfigEntryAuthFailed("Bitpanda API key is invalid") from err
        except BitpandaApiError as err:
            assets = {}
            metadata_error = f"asset_metadata:{err.code}"
            self._remember(metadata_error)

        earn_error: str | None = None
        try:
            earn_configs = await self.client.async_earn_configs(asset_ids)
        except BitpandaAuthenticationError as err:
            raise ConfigEntryAuthFailed("Bitpanda API key is invalid") from err
        except BitpandaApiError as err:
            earn_configs = None
            earn_error = f"earn_configs:{err.code}"
            self._remember(earn_error)

        for item in raw:
            currency_id = item.get("currencyId")
            if isinstance(item.get("assetId"), str) or not isinstance(currency_id, str):
                continue
            if currency := self.currencies.get(currency_id):
                assets[currency_id] = AssetMetadata(
                    currency_id,
                    currency.symbol,
                    currency.name,
                    "FIAT",
                    "FIAT",
                )

        snapshot = build_snapshot(
            raw,
            assets,
            self.currency,
            self.include_zero_balances,
            earn_configs,
        )
        enrichment_errors = tuple(
            error for error in (metadata_error, earn_error) if error is not None
        )
        if enrichment_errors:
            snapshot = replace(
                snapshot,
                completeness=Completeness.PARTIAL,
                errors=(*enrichment_errors, *snapshot.errors),
            )
        return snapshot

    def _remember(self, error: str) -> None:
        self.recent_errors = [*self.recent_errors, error][-20:]
