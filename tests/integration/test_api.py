"""New Bitpanda Public API client parsing and error behavior."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from custom_components.bitpanda.api import (
    BitpandaAuthenticationError,
    BitpandaClient,
    BitpandaRateLimitError,
)


class Response:
    def __init__(self, status: int, payload: Any) -> None:
        self.status = status
        self.payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def json(self, content_type=None):
        return self.payload


class Session:
    def __init__(self, *responses: Response) -> None:
        self.responses = list(responses)
        self.requests: list[tuple[str, dict[str, Any]]] = []

    def get(self, url: str, **kwargs: Any) -> Response:
        self.requests.append((url, kwargs))
        return self.responses.pop(0)


@pytest.mark.asyncio
async def test_currency_and_portfolio_use_new_public_api_contract() -> None:
    session = Session(
        Response(
            200,
            {
                "data": [
                    {
                        "id": "currency-eur",
                        "symbol": "EUR",
                        "name": "Euro",
                    }
                ]
            },
        ),
        Response(200, {"data": [{"assetId": "asset-eth"}]}),
    )
    client = BitpandaClient(session, "secret")  # type: ignore[arg-type]

    currency = await client.async_currency("eur")
    portfolio = await client.async_portfolio(currency.currency_id)
    cached_currencies = await client.async_currencies()

    assert currency.currency_id == "currency-eur"
    assert cached_currencies == (currency,)
    assert portfolio == [{"assetId": "asset-eth"}]
    assert session.requests[0][0] == "https://api.public.bitpanda.com/v1/currencies"
    assert session.requests[1][1]["params"] == {
        "equivalent_currency_id": "currency-eur"
    }
    assert session.requests[1][1]["headers"] == {"x-api-key": "secret"}
    assert len(session.requests) == 2


@pytest.mark.asyncio
async def test_live_snake_case_portfolio_contract_is_normalized() -> None:
    client = BitpandaClient(  # type: ignore[arg-type]
        Session(
            Response(
                200,
                {
                    "data": [
                        {
                            "asset_id": "asset-eth",
                            "balance": {"value": "0.5", "asset_id": "asset-eth"},
                            "available_balance": {"value": "0.4"},
                            "invested_amount": {"value": "1000"},
                            "average_buy_price": {"value": "2000"},
                            "currency_balance": {"value": "1500"},
                            "total_return": {"value": "500"},
                            "total_return_percent": "50",
                        },
                        {
                            "currency_id": "currency-eur",
                            "balance": {"value": "25"},
                            "available_balance": {"value": "25"},
                        },
                    ]
                },
            )
        ),
        "secret",
    )

    portfolio = await client.async_portfolio("currency-eur")

    assert portfolio[0]["assetId"] == "asset-eth"
    assert portfolio[0]["availableBalance"] == {"value": "0.4"}
    assert portfolio[0]["currencyBalance"] == {"value": "1500"}
    assert portfolio[0]["totalReturnPercent"] == "50"
    assert portfolio[1] == {
        "currencyId": "currency-eur",
        "balance": {"value": "25"},
        "availableBalance": {"value": "25"},
    }


@pytest.mark.asyncio
async def test_assets_follow_new_cursor_pagination_and_are_cached() -> None:
    session = Session(
        Response(
            200,
            {
                "data": [
                    {
                        "id": "asset-eth",
                        "symbol": "ETH",
                        "name": "Ethereum",
                        "type": "CRYPTO",
                        "group": "CRYPTOCOIN",
                    }
                ],
                "has_next_page": True,
                "next_cursor": "next",
            },
        ),
        Response(
            200,
            {
                "data": [
                    {
                        "id": "asset-atom",
                        "symbol": "ATOM",
                        "name": "Cosmos",
                        "type": "CRYPTO",
                        "group": "CRYPTOCOIN",
                    }
                ],
                "has_next_page": False,
            },
        ),
    )
    client = BitpandaClient(session, "secret")  # type: ignore[arg-type]

    assets = await client.async_assets({"asset-eth", "asset-atom"})
    cached = await client.async_assets({"asset-eth"})

    assert assets["asset-atom"].name == "Cosmos"
    assert cached["asset-eth"].symbol == "ETH"
    assert len(session.requests) == 2
    assert session.requests[1][1]["params"]["cursor"] == "next"


@pytest.mark.asyncio
async def test_earn_configs_normalize_apr_and_follow_live_pagination() -> None:
    session = Session(
        Response(
            200,
            {
                "data": [
                    {
                        "id": "config-eth",
                        "asset_id": "asset-eth",
                        "annual_percentage_rate": 0.024,
                        "type": "LOCKED",
                        "mode": "STAKING_EARN",
                        "enabled": True,
                        "soldout": False,
                    }
                ],
                "has_next_page": True,
                "next_cursor": "next",
            },
        ),
        Response(
            200,
            {
                "data": [
                    {
                        "id": "config-atom",
                        "assetId": "asset-atom",
                        "annualPercentageRate": 0.1486,
                        "type": "FLEXIBLE",
                        "mode": "STAKING_EARN",
                        "enabled": True,
                        "soldout": True,
                    }
                ],
                "hasNextPage": False,
            },
        ),
    )
    client = BitpandaClient(session, "secret")  # type: ignore[arg-type]

    configs = await client.async_earn_configs({"asset-eth", "asset-atom"})

    assert configs["asset-eth"][0].annual_percentage_rate == Decimal("0.024")
    assert configs["asset-eth"][0].available is True
    assert configs["asset-atom"][0].annual_percentage_rate == Decimal("0.1486")
    assert configs["asset-atom"][0].available is False
    assert session.requests[1][1]["params"]["cursor"] == "next"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "exception"),
    [(401, BitpandaAuthenticationError), (429, BitpandaRateLimitError)],
)
async def test_api_errors_are_typed(status: int, exception: type[Exception]) -> None:
    client = BitpandaClient(  # type: ignore[arg-type]
        Session(Response(status, {"error": {"code": "denied"}})),
        "secret",
    )
    with pytest.raises(exception, match="denied"):
        await client.async_currencies()
