"""Small async client for Bitpanda's new Public API."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from typing import Any

from aiohttp import ClientError, ClientSession, ClientTimeout

from .const import API_BASE_URL
from .models import AssetMetadata, Currency, EarnConfig


class BitpandaApiError(Exception):
    """Base API error with a safe, non-secret reason code."""

    def __init__(self, status: int, code: str) -> None:
        super().__init__(f"Bitpanda API error {status}: {code}")
        self.status = status
        self.code = code


class BitpandaAuthenticationError(BitpandaApiError):
    """The API key is missing, invalid, or lacks the read scope."""


class BitpandaRateLimitError(BitpandaApiError):
    """The per-user API limit was exceeded."""


class BitpandaClient:
    """Read-only client limited to metadata and portfolio endpoints."""

    def __init__(
        self,
        session: ClientSession,
        api_key: str,
        base_url: str = API_BASE_URL,
    ) -> None:
        self._session = session
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._asset_cache: dict[str, AssetMetadata] = {}
        self._currency_cache: tuple[Currency, ...] | None = None

    async def _async_get(
        self, path: str, params: Mapping[str, str | int] | None = None
    ) -> dict[str, Any]:
        try:
            async with self._session.get(
                f"{self._base_url}{path}",
                params=params,
                headers={"x-api-key": self._api_key},
                timeout=ClientTimeout(total=20),
            ) as response:
                try:
                    payload = await response.json(content_type=None)
                except (ValueError, TypeError) as err:
                    raise BitpandaApiError(
                        response.status, "invalid_json_response"
                    ) from err
                if response.status == 401:
                    raise BitpandaAuthenticationError(
                        response.status, _error_code(payload, "unauthorized")
                    )
                if response.status == 429:
                    raise BitpandaRateLimitError(
                        response.status, _error_code(payload, "rate_limited")
                    )
                if response.status >= 400:
                    raise BitpandaApiError(
                        response.status, _error_code(payload, "request_failed")
                    )
                if not isinstance(payload, dict):
                    raise BitpandaApiError(response.status, "invalid_response_shape")
                return payload
        except BitpandaApiError:
            raise
        except (ClientError, TimeoutError) as err:
            raise BitpandaApiError(0, type(err).__name__) from err

    async def async_currencies(self) -> tuple[Currency, ...]:
        """Return supported fiat currencies."""
        if self._currency_cache is not None:
            return self._currency_cache
        payload = await self._async_get("/v1/currencies")
        data = payload.get("data")
        if not isinstance(data, list):
            raise BitpandaApiError(200, "currencies_data_is_not_a_list")
        currencies: list[Currency] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            currency_id = item.get("id")
            symbol = item.get("symbol")
            if not isinstance(currency_id, str) or not isinstance(symbol, str):
                continue
            currencies.append(
                Currency(currency_id, symbol.upper(), str(item.get("name") or symbol))
            )
        if not currencies:
            raise BitpandaApiError(200, "no_currencies_returned")
        self._currency_cache = tuple(currencies)
        return self._currency_cache

    async def async_currency(self, symbol: str) -> Currency:
        """Resolve a display currency by symbol."""
        normalized = symbol.upper()
        for currency in await self.async_currencies():
            if currency.symbol == normalized:
                return currency
        raise BitpandaApiError(200, f"currency_{normalized}_not_found")

    async def async_portfolio(
        self, equivalent_currency_id: str
    ) -> list[dict[str, Any]]:
        """Return authoritative positions and Bitpanda-calculated performance."""
        payload = await self._async_get(
            "/v1/portfolio",
            {"equivalent_currency_id": equivalent_currency_id},
        )
        data = payload.get("data")
        if not isinstance(data, list):
            raise BitpandaApiError(200, "portfolio_data_is_not_a_list")
        return [_portfolio_item(item) for item in data if isinstance(item, dict)]

    async def async_assets(self, asset_ids: set[str]) -> dict[str, AssetMetadata]:
        """Resolve only missing asset metadata, following cursor pagination."""
        missing = asset_ids - self._asset_cache.keys()
        if not missing:
            return {item: self._asset_cache[item] for item in asset_ids}

        cursor: str | None = None
        for _page in range(100):
            params: dict[str, str | int] = {
                "id": ",".join(sorted(missing)),
                "page_size": 100,
            }
            if cursor:
                params["cursor"] = cursor
            payload = await self._async_get("/v1/assets", params)
            data = payload.get("data")
            if not isinstance(data, list):
                raise BitpandaApiError(200, "assets_data_is_not_a_list")
            for item in data:
                metadata = _asset(item)
                if metadata:
                    self._asset_cache[metadata.asset_id] = metadata
            if not _first(payload, "hasNextPage", "has_next_page"):
                break
            next_cursor = _first(payload, "nextCursor", "next_cursor")
            if (
                not isinstance(next_cursor, str)
                or not next_cursor
                or next_cursor == cursor
            ):
                raise BitpandaApiError(200, "invalid_asset_pagination_cursor")
            cursor = next_cursor
        else:
            raise BitpandaApiError(200, "asset_pagination_limit_exceeded")
        return {
            item: self._asset_cache[item]
            for item in asset_ids
            if item in self._asset_cache
        }

    async def async_earn_configs(
        self, asset_ids: set[str]
    ) -> dict[str, tuple[EarnConfig, ...]]:
        """Return current Earn configurations for held assets."""
        if not asset_ids:
            return {}
        configs: dict[str, list[EarnConfig]] = {}
        cursor: str | None = None
        for _page in range(100):
            params: dict[str, str | int] = {"page_size": 100}
            if cursor:
                params["cursor"] = cursor
            payload = await self._async_get("/v1/earn/configs", params)
            data = payload.get("data")
            if not isinstance(data, list):
                raise BitpandaApiError(200, "earn_configs_data_is_not_a_list")
            for item in data:
                config = _earn_config(item)
                if config and config.asset_id in asset_ids:
                    configs.setdefault(config.asset_id, []).append(config)
            if not _first(payload, "hasNextPage", "has_next_page"):
                break
            next_cursor = _first(payload, "nextCursor", "next_cursor")
            if (
                not isinstance(next_cursor, str)
                or not next_cursor
                or next_cursor == cursor
            ):
                raise BitpandaApiError(200, "invalid_earn_pagination_cursor")
            cursor = next_cursor
        else:
            raise BitpandaApiError(200, "earn_pagination_limit_exceeded")
        return {
            asset_id: tuple(sorted(items, key=lambda item: item.config_id))
            for asset_id, items in configs.items()
        }


def _portfolio_item(value: dict[str, Any]) -> dict[str, Any]:
    """Normalize the documented camelCase and live snake_case contracts."""
    aliases = {
        "assetId": ("assetId", "asset_id"),
        "currencyId": ("currencyId", "currency_id"),
        "balance": ("balance",),
        "availableBalance": ("availableBalance", "available_balance"),
        "investedAmount": ("investedAmount", "invested_amount"),
        "averageBuyPrice": ("averageBuyPrice", "average_buy_price"),
        "currencyBalance": ("currencyBalance", "currency_balance"),
        "totalReturn": ("totalReturn", "total_return"),
        "totalReturnPercent": ("totalReturnPercent", "total_return_percent"),
    }
    return {
        normalized: field
        for normalized, names in aliases.items()
        if (field := _first(value, *names)) is not None
    }


def _earn_config(value: Any) -> EarnConfig | None:
    """Normalize one documented camelCase or live snake_case Earn config."""
    if not isinstance(value, dict):
        return None
    config_id = _first(value, "id")
    asset_id = _first(value, "assetId", "asset_id")
    rate = _decimal(_first(value, "annualPercentageRate", "annual_percentage_rate"))
    earn_type = _first(value, "type")
    mode = _first(value, "mode")
    enabled = _first(value, "enabled")
    sold_out = _first(value, "soldout", "sold_out")
    if (
        not isinstance(config_id, str)
        or not isinstance(asset_id, str)
        or rate is None
        or rate < 0
        or not isinstance(earn_type, str)
        or not isinstance(mode, str)
        or not isinstance(enabled, bool)
        or not isinstance(sold_out, bool)
    ):
        return None
    return EarnConfig(
        config_id,
        asset_id,
        rate,
        earn_type,
        mode,
        enabled,
        sold_out,
    )


def _first(value: Mapping[str, Any], *names: str) -> Any:
    """Return the first present spelling, preserving false and zero values."""
    for name in names:
        if name in value:
            return value[name]
    return None


def _decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return result if result.is_finite() else None


def _asset(value: Any) -> AssetMetadata | None:
    if not isinstance(value, dict):
        return None
    asset_id, symbol = value.get("id"), value.get("symbol")
    if not isinstance(asset_id, str) or not isinstance(symbol, str):
        return None
    isin = value.get("isin")
    return AssetMetadata(
        asset_id=asset_id,
        symbol=symbol.upper(),
        name=str(value.get("name") or symbol),
        asset_type=str(value.get("type") or "unknown"),
        group=str(value.get("group") or "unknown"),
        isin=isin if isinstance(isin, str) and isin else None,
    )


def _error_code(payload: Any, fallback: str) -> str:
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict) and isinstance(error.get("code"), str):
            return error["code"]
    return fallback
