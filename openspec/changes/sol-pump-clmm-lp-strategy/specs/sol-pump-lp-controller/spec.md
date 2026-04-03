## ADDED Requirements

### Requirement: LPRebalancer manages CLMM position lifecycle
`LPRebalancer` (used directly, no subclass) SHALL manage the full position lifecycle: open, monitor in-range/out-of-range, close, and reopen at new bounds. All executor lifecycle, KEEP logic, price limit anchoring, and closed-amount rollover are provided by `LPRebalancer` without modification.

#### Scenario: Position opens on start
- **WHEN** the controller starts with no active executor
- **THEN** it SHALL create a BOTH-sided position centered on current price within the configured bounds

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
