## ADDED Requirements

### Requirement: LPRebalancer manages CLMM position lifecycle
`LPRebalancer` (used directly, no subclass) SHALL manage the full position lifecycle: open, monitor in-range/out-of-range, close, and reopen at new bounds. All executor lifecycle, KEEP logic, price limit anchoring, and closed-amount rollover are provided by `LPRebalancer` without modification.

#### Scenario: Position opens on start (no existing on-chain position)
- **WHEN** the controller starts with no active executor AND no position exists on-chain in the pool
- **THEN** it SHALL create a BOTH-sided position centered on current price within the configured bounds

#### Scenario: Existing on-chain position adopted on restart
- **WHEN** the bot restarts and an open LP position already exists in the pool for this wallet
- **THEN** `LPExecutor.on_start()` SHALL adopt that position instead of opening a new one — setting `lp_position_state.position_address`, bounds, and amounts from the on-chain data
- **AND** the executor SHALL transition to `IN_RANGE` or `OUT_OF_RANGE` on the first `control_task` tick without calling `_create_position()`

#### Scenario: Multiple positions in pool — rank-based matching
- **WHEN** multiple positions exist in the same pool (e.g. narrow + wide)
- **THEN** each executor SHALL adopt the position whose relative width `(upper-lower)/lower` is at the same rank as the executor's configured width among all on-chain positions
- **AND** the narrow executor (smaller `position_width_pct`) SHALL always adopt the narrower on-chain position, the wide executor the wider one — regardless of the absolute price values
- ⚠️ **Pitfall**: matching by absolute width values breaks when config is updated; rank-based matching is robust to any width change as long as the relative ordering (narrow < wide) is preserved

#### Scenario: KEEP fires when BUY position is at buy_price_max
- **WHEN** an active BUY position's upper bound equals `buy_price_max` and price is above range
- **THEN** the controller SHALL return no executor actions (KEEP — no rebalance)

#### Scenario: Fee rollover on rebalance
- **WHEN** a position closes after going out of range
- **THEN** the next position's amounts SHALL be taken from the closed position's returned amounts (which include accumulated fees), compounding automatically

---

### Requirement: Rebalance after sustained out-of-range
The controller SHALL wait `rebalance_seconds` (180s) with price at least `rebalance_threshold_pct` (0.5%) beyond the range boundary before triggering a rebalance.

#### Scenario: No rebalance on brief out-of-range
- **WHEN** price exits the range for less than 180 seconds
- **THEN** the controller SHALL NOT issue a `StopExecutorAction`

#### Scenario: Rebalance after timer expires
- **WHEN** price remains outside the range for 180+ seconds AND is 0.5%+ beyond the boundary
- **THEN** the controller SHALL issue a `StopExecutorAction` to close the position and open a new one at updated bounds
