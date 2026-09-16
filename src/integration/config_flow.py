"""UI configuration for Bitpanda's read-only Public API."""

from __future__ import annotations

from hashlib import sha256
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import BitpandaApiError, BitpandaAuthenticationError, BitpandaClient
from .const import (
    CONF_API_KEY,
    CONF_INCLUDE_ZERO_BALANCES,
    CONF_SCAN_INTERVAL,
    DEFAULT_INCLUDE_ZERO_BALANCES,
    DEFAULT_SCAN_INTERVAL,
    DISPLAY_CURRENCY,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)


class CannotConnect(Exception):
    """The service could not be reached or returned an invalid response."""


async def async_validate_input(hass: HomeAssistant, api_key: str) -> str:
    """Validate read access and return a non-secret account fingerprint."""
    client = BitpandaClient(async_get_clientsession(hass), api_key)
    try:
        currency = await client.async_currency(DISPLAY_CURRENCY)
        await client.async_portfolio(currency.currency_id)
    except BitpandaAuthenticationError:
        raise
    except BitpandaApiError as err:
        raise CannotConnect from err
    return sha256(api_key.encode()).hexdigest()[:20]


class BitpandaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure a Bitpanda account."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            api_key = str(user_input[CONF_API_KEY]).strip()
            try:
                fingerprint = await async_validate_input(self.hass, api_key)
            except BitpandaAuthenticationError:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(fingerprint)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Bitpanda Portfolio",
                    data={CONF_API_KEY: api_key},
                )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD
                        )
                    )
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        """Start API-key replacement without changing entity identity."""
        del entry_data
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            api_key = str(user_input[CONF_API_KEY]).strip()
            try:
                await async_validate_input(self.hass, api_key)
            except BitpandaAuthenticationError:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            else:
                if self._reauth_entry is None:
                    return self.async_abort(reason="reauth_failed")
                return self.async_update_and_abort(
                    self._reauth_entry,
                    data={**self._reauth_entry.data, CONF_API_KEY: api_key},
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD
                        )
                    )
                }
            ),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> BitpandaOptionsFlow:
        return BitpandaOptionsFlow()


class BitpandaOptionsFlow(config_entries.OptionsFlow):
    """Edit polling and zero-balance visibility."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL)),
                    vol.Required(
                        CONF_INCLUDE_ZERO_BALANCES,
                        default=self.config_entry.options.get(
                            CONF_INCLUDE_ZERO_BALANCES,
                            DEFAULT_INCLUDE_ZERO_BALANCES,
                        ),
                    ): selector.BooleanSelector(),
                }
            ),
        )
