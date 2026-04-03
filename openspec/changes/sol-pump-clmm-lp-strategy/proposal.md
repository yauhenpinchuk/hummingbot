## Why

Providing liquidity manually in a Raydium CLMM pool is impractical — concentrated positions go out of range within hours on volatile pairs, leaving capital idle and earning zero fees. An automated rebalancer that repositions continuously captures 24h APR of 32–150% (pool-validated) while the operator holds SOL and PUMP long-term regardless of direction.

## What Changes

- **New controller** `controllers/generic/sol_pump_lp/sol_pump_lp.py` — extends `LPRebalancer` with volatility-adaptive range width, asymmetric range skew, and a momentum filter to reduce unnecessary rebalances
- **New config file** `conf_sol_pump_lp.yml` — YAML strategy config for the SOL-PUMP pool on Raydium CLMM (pool `45ssPkUQs1ssbeDqxD2mZrMdJYAXF7GyQyhS5xDXuWC5`)
- **Fee compounding** — closed position amounts (including accumulated fees) are automatically rolled into the next position size via existing `_last_closed_`* mechanism; add explicit reporting
- **P&L tracker** — log-level reporting of: total fees earned, rebalance count, gas cost estimate, net P&L vs hold

## Capabilities

### New Capabilities

- `sol-pump-lp-controller`: Automated concentrated-liquidity market-making controller for the Raydium CLMM SOL-PUMP pool — handles position open/close, out-of-range detection, rebalancing with momentum filter, volatility-adaptive range width, asymmetric range skew, fee compounding, and P&L reporting
- `sol-pump-lp-config`: Strategy YAML configuration for the SOL-PUMP Raydium CLMM pool including price limits, range parameters, capital sizing, and rebalance timing

### Modified Capabilities



## Impact

- **New files**: `controllers/generic/sol_pump_lp/sol_pump_lp.py`, `controllers/generic/sol_pump_lp/__init__.py`, `conf/sol_pump_lp.yml`
- **Existing infrastructure used unchanged**: `LPRebalancer` (base class), `LPExecutor`, `GatewayLp`, `raydium/clmm` gateway connector
- **Gateway**: `raydium/clmm` is production-ready (`@raydium-io/raydium-sdk-v2 v0.1.141-alpha`) — all LP operations implemented; no gateway changes needed
- **Pool**: `45ssPkUQs1ssbeDqxD2mZrMdJYAXF7GyQyhS5xDXuWC5` (WSOL/PUMP, 0.1% fee, tick spacing 10, TVL $173k, monthly volume $21.7M, monthly APR 150%)
- **Capital**: $3,000–$4,000 USD split ~50/50 SOL + PUMP; `total_amount_quote` expressed in SOL
- **Dependencies**: none new — all Python packages and gateway SDKs already present
