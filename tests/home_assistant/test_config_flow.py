"""Home Assistant config-flow behavior."""

from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.bitpanda.api import BitpandaAuthenticationError
from custom_components.bitpanda.const import CONF_API_KEY, DOMAIN


async def test_user_flow_creates_secret_config_entry(hass) -> None:
    with (
        patch(
            "custom_components.bitpanda.config_flow.async_validate_input",
            AsyncMock(return_value="fingerprint"),
        ),
        patch(
            "custom_components.bitpanda.async_setup_entry",
            AsyncMock(return_value=True),
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_API_KEY: "secret-key"}
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Bitpanda Portfolio"
    assert result["data"] == {CONF_API_KEY: "secret-key"}
    assert result["result"].unique_id == "fingerprint"


async def test_user_flow_rejects_invalid_api_key(hass) -> None:
    with patch(
        "custom_components.bitpanda.config_flow.async_validate_input",
        AsyncMock(side_effect=BitpandaAuthenticationError(401, "unauthorized")),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_API_KEY: "bad-key"}
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}
