# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install / create conda environment (uses conda, never pip directly for env setup)
make install

# Compile Cython extensions in-place (required after changing .pyx files)
python setup.py build_ext --inplace

# Run unit tests with coverage (excludes known-broken suites)
make test

# Run a single test file
conda run -n hummingbot pytest test/hummingbot/connector/exchange/binance/test_binance_exchange.py -v

# Check diff coverage locally against development branch (CI requires ≥80%)
make development-diff-cover

# Run the application
make run

# Docker: build image, then deploy full stack (includes optional Gateway middleware)
make build
make setup   # configure Gateway
make deploy  # docker compose up
```

### Known-broken test suites (excluded from `make test`)
- `test/mock/`
- `test/hummingbot/connector/exchange/ndax/`
- `test/hummingbot/connector/derivative/dydx_v4_perpetual/`
- `test/hummingbot/remote_iface/`
- `test/connector/utilities/oms_connector/`
- `test/hummingbot/strategy/amm_arb/`
- `test/hummingbot/strategy/cross_exchange_market_making/`

## Architecture

Hummingbot is an async, event-driven trading bot. Performance-critical paths are compiled via Cython (`.pyx`/`.pxd` files); the rest is pure Python 3.10+.

```
hummingbot/
├── connector/          # Exchange connectors (40+ exchanges)
│   ├── exchange/       # Spot connectors
│   ├── derivative/     # Perpetual/futures connectors
│   └── gateway/        # DEX/AMM connectors (via Gateway middleware)
├── strategy/           # V1 strategies (Cython, legacy)
├── strategy_v2/        # V2 smart-component framework (pure Python)
│   ├── controllers/    # Decision logic
│   ├── executors/      # Order execution logic
│   └── backtesting/    # Backtesting engine
├── core/               # Order book, event system, rate oracle, web assistant
├── client/             # CLI UI and commands
└── model/              # DB models / migrations
test/
└── hummingbot/         # Mirrors source tree structure
```

**Strategies** call into **connectors** via an event-driven interface. Connectors emit `BuyOrderCreatedEvent`, `OrderFilledEvent`, etc.; strategies subscribe and react. All network I/O is async (`asyncio` + `aiohttp`). The `Clock` (Cython) drives strategy tick execution.

## Key Patterns

**Connector structure** — every connector under `connector/exchange/<name>/` has these files:
- `<name>_exchange.py` — main class inheriting `ExchangePyBase`
- `<name>_api_order_book_data_source.py` — order book websocket/REST
- `<name>_api_user_stream_data_source.py` — order/fill/balance stream
- `<name>_auth.py` — API key/signature logic (inherits `AuthBase`)
- `<name>_constants.py` — rate limits (`RATE_LIMITS`), URL paths, endpoint IDs
- `<name>_web_utils.py` — `build_api_factory()`, `public_rest_url()`, `private_rest_url()`

**Rate limiting** uses `AsyncThrottler` fed by `RateLimit` objects with `LinkedLimitWeightPair` for shared pools. Define all limits in `<name>_constants.py`.

**Decimal precision** — all monetary values use `Decimal` throughout; never `float`.

**V1 strategies** live under `strategy/<name>/` as Cython (`.pyx`) with a `start.py` for CLI wiring. **V2 strategies** live under `strategy_v2/controllers/` as pure Python, driven by executors.

**Testing connectors** — subclass `AbstractExchangeConnectorTests.ExchangeConnectorTests` and provide mock URL properties + JSON responses. Use `aioresponses` to mock HTTP. Use `IsolatedAsyncioWrapperTestCase` as the async test base. Do **not** use `unittest.IsolatedAsyncioTestCase` directly.

**No `__init__.py` in test directories** — some test subdirectories intentionally omit `__init__.py` to avoid shadowing source packages.

## Code Style

- Line length: **120** characters (flake8, isort, autopep8)
- flake8 ignores globally: E251, E501, E702, W504, W503
- Imports sorted via isort (`pyproject.toml` config); run `isort` before committing
- Pre-commit hooks enforce trailing whitespace, flake8, autopep8, isort; install with `pre-commit install`

## Contribution Workflow

- Branch from **`development`** (not `master`); PR target is `development`
- Branch prefixes: `feat/`, `fix/`, `refactor/`, `doc/`
- Commit prefix convention: `(feat)`, `(fix)`, `(refactor)`, `(cleanup)`, `(doc)`
- PRs require **≥80% diff coverage**; global floor is 70%
- Coverage excludes UI, config, gateway, and strategy modules (see `.coveragerc`)

## Environment Variables

The application reads credentials and config from YAML files in `conf/` (created on first run) and optionally from environment variables for Docker deployments. `PYTHONPATH=${PWD}` must be set for local development without installing the package.
