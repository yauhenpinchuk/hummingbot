## MODIFIED Requirements

### Requirement: Narrow controller range and timing
`sol_pump_lp_narrow.yml` SHALL specify:
- `position_width_pct: '5.5'` (±2.75% — calibrated to stable-regime daily move of ~3.1%)
- `position_offset_pct: '0.4'` (slightly larger buffer for 5.5% range vs. previous 0.3%)
- `rebalance_seconds: 300` (unchanged — 5 min out-of-range before rebalancing)
- `rebalance_threshold_pct: '0.5'` (unchanged)

#### Scenario: Narrow position rebalances after 5 min OOR
- **WHEN** price remains outside the narrow range for 300+ seconds AND is 0.5%+ beyond the boundary
- **THEN** the narrow controller SHALL issue a `StopExecutorAction`

#### Scenario: Narrow position stays in-range on typical daily move
- **WHEN** price moves less than 2.75% from the position's center tick
- **THEN** the narrow position SHALL remain active and earn fees without rebalancing

---

### Requirement: Wide controller range and timing
`sol_pump_lp_wide.yml` SHALL specify:
- `position_width_pct: '26.0'` (±13% — covers stable-regime median monthly range of ~25%)
- `position_offset_pct: '0.5'` (unchanged)
- `rebalance_seconds: 1800` (30 min out-of-range before rebalancing — slower than narrow)
- `rebalance_threshold_pct: '1.5'` (price must be 1.5% beyond bounds before timer starts)

#### Scenario: Wide position does not rebalance on narrow rebalance event
- **WHEN** the narrow position goes OOR and rebalances
- **THEN** the wide position SHALL remain open (its 26% range covers the narrow's 5.5% moves)

#### Scenario: Wide position waits for confirmed break before rebalancing
- **WHEN** price exits the wide range but returns inside within 30 minutes
- **THEN** the wide controller SHALL NOT rebalance (timer resets on re-entry)

---

### Requirement: Price limits bracket the stable-regime trading range

**Narrow** (`position_width_pct: 5.5`), calibrated to Oct 2025–Apr 2026 percentile distribution:
```
buy_price_min:  '38000'   # p10 — stop buying SOL if PUMP collapses
buy_price_max:  '60000'   # p80 — anchor for BUY positions (KEEP logic)
sell_price_min: '44000'   # above p25 with buffer — anchor for SELL positions (KEEP logic)
sell_price_max: '68000'   # p95 — stop selling if PUMP spikes hard
```

**Wide** (`position_width_pct: 26.0`):
```
buy_price_min:  '32000'   # p3 — hard floor, stop buying if PUMP collapses
buy_price_max:  '70000'   # p95–p99 range — wider bracket for wider position
sell_price_min: '38000'   # p10 — anchor for SELL positions
sell_price_max: '76000'   # ATH + ~2% buffer — stop selling if PUMP moons
```

#### Scenario: KEEP fires when BUY position is anchored at buy_price_max
- **WHEN** a BUY position's upper bound equals `buy_price_max` and price is above range
- **THEN** the controller SHALL KEEP the position and not rebalance further upward

#### Scenario: KEEP fires when SELL position is anchored at sell_price_min
- **WHEN** a SELL position's lower bound equals `sell_price_min` and price is below range
- **THEN** the controller SHALL KEEP the position and not rebalance further downward

#### Scenario: Buy-side not prematurely capped near current price
- **WHEN** current price is ~48,000–52,000 PUMP/SOL
- **THEN** narrow `buy_price_max` (60,000) SHALL be at least 15% above current price, ensuring KEEP does not trigger during a normal rally
