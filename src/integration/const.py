"""Constants for the Bitpanda integration."""

from datetime import timedelta

DOMAIN = "bitpanda"

CONF_API_KEY = "api_key"
CONF_INCLUDE_ZERO_BALANCES = "include_zero_balances"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_INCLUDE_ZERO_BALANCES = False
DEFAULT_SCAN_INTERVAL = 900
MIN_SCAN_INTERVAL = 300
DEFAULT_UPDATE_INTERVAL = timedelta(seconds=DEFAULT_SCAN_INTERVAL)

API_BASE_URL = "https://api.public.bitpanda.com"
DISPLAY_CURRENCY = "EUR"

ATTR_INTEGRATION_DOMAIN = "integration_domain"
ATTR_CONFIG_ENTRY_ID = "config_entry_id"
ATTR_RESOURCE_TYPE = "resource_type"
ATTR_RESOURCE_ID = "resource_id"
ATTR_METRIC_ID = "metric_id"
ATTR_ASSET_ID = "asset_id"
ATTR_ASSET_SYMBOL = "asset_symbol"

RESOURCE_PORTFOLIO = "portfolio"
RESOURCE_ASSET = "asset"
