## Why

The SOL-PUMP LP strategy's current position widths and price limits were set using only ~30 days of data from the PUMP token's volatile launch period (July–August 2025), which is not representative of the asset's mature behavior. Nine months of data (Jul 2025–Apr 2026) show the pair has settled into a distinct stable regime since October 2025, with daily moves averaging 3.1% and monthly ranges of ~25%—significantly calmer than the launch spike. The current narrow range (4%) is too tight, leaving the position idle 69% of the time and triggering ~0.7 rebalances per day; the wide range (16%) is not wide enough to serve as a real monthly safety net given the actual historical spread.

## What Changes

- `position_width_pct` for the narrow controller: `4.0` → `5.5` (better fit for 3.1% daily move in stable regime; ~1.5 day average position life vs. ~1.4 now)
- `position_width_pct` for the wide controller: `16.0` → `26.0` (covers the median monthly range of ~25%; reduces rebalances from ~65 to ~25 over 9 months)
- `rebalance_seconds` for the wide controller: `900` → `1800` (slower reaction appropriate for a wider safety-net position)
- `rebalance_threshold_pct` for the wide controller: `1.0` → `1.5` (reduces noise-triggered rebalances on the wider range)
- `position_offset_pct` for the narrow controller: `0.3` → `0.4` (slightly larger buffer; 5% range has more room)
- Price limits for both controllers updated to reflect 9-month percentile distribution:
  - Narrow `buy_price_max`: `51500` → `60000` (p80 ≈ 57,022; raised above to avoid capping buy-side while price sits near median)
  - Narrow `sell_price_max`: `56000` → `68000` (p95 ≈ 67,613)
  - Wide `buy_price_max`: `55000` → `70000` (p95–p99 range)
  - Wide `sell_price_max`: `65000` → `76000` (≈ATH + 2% buffer)
  - Floor limits (`buy_price_min`, `sell_price_min`) preserved — downside remains conservatively anchored at p5/p10

## Capabilities

### New Capabilities
- None — this is a parameter-only tuning change; no new capabilities are introduced.

### Modified Capabilities
- `sol-pump-lp-config`: Requirements for `position_width_pct`, `rebalance_seconds`, `rebalance_threshold_pct`, `position_offset_pct`, and the price limit values are all changing for both controllers.

## Impact

- **Files changed**: `conf/controllers/sol_pump_lp_narrow.yml`, `conf/controllers/sol_pump_lp_wide.yml`
- **No code changes**: controller logic (`lp_rebalancer`) is untouched
- **Operational impact**: existing live positions will rebalance into the new widths on their next natural rebalance cycle — no manual position close required
- **Risk**: wider ranges = lower fee concentration per unit of capital; the trade-off is fewer rebalance events and more time in-range earning fees
