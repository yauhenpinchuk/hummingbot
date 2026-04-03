## ADDED Requirements

### Requirement: Strategy YAML config file exists and is valid
A file `conf/sol_pump_lp.yml` SHALL exist and be loadable by Hummingbot's `v2_with_controllers.py` script. It SHALL reference `lp_rebalancer` as the controller and the Raydium CLMM SOL-PUMP pool.

#### Scenario: Config loads without error
- **WHEN** Hummingbot starts with `--script v2_with_controllers.py --conf conf/sol_pump_lp.yml`
- **THEN** the strategy SHALL initialize, connect to `raydium/clmm`, and begin monitoring without errors

---

### Requirement: Pool and connector settings
The config SHALL specify:
- `connector_name: raydium/clmm`
- `network: mainnet-beta`
- `pool_address: 45ssPkUQs1ssbeDqxD2mZrMdJYAXF7GyQyhS5xDXuWC5`
- `trading_pair: SOL-PUMP` — confirmed: gateway token list (`conf/tokens/solana/mainnet-beta.json`) maps `So111...112` → `SOL`, `pumpC...Dfn` → `PUMP`

#### Scenario: Pool address matches live pool
- **WHEN** gateway `pool-info` is called with `pool_address=45ssPkUQs1ssbeDqxD2mZrMdJYAXF7GyQyhS5xDXuWC5`
- **THEN** it SHALL return a pool with fee=0.1%, tick_spacing=10, tokens WSOL + PUMP

---

### Requirement: Capital and initial position settings
The config SHALL deploy the operator's combined SOL+PUMP holdings (~$3,000–$4,000):
- `total_amount_quote`: expressed in SOL; start at ~3.3 SOL ($500 test), scale to ~23 SOL ($3,500) after validation
- `side: 0` (BOTH-sided — operator holds both tokens)
- `position_offset_pct: '0.3'` (safety buffer for price shift during TX submission)

#### Scenario: Both-sided position opens on start
- **WHEN** the controller starts and no active executor exists
- **THEN** it SHALL create a BOTH-sided position centered on current price

---

### Requirement: Range and rebalance timing parameters
The config SHALL specify:
- `position_width_pct: '6.0'` (±3% — contains a typical 24h price move for this pool)
- `rebalance_seconds: 180` (3 minutes out-of-range before rebalancing)
- `rebalance_threshold_pct: '0.5'` (price must be 0.5% beyond bounds before timer starts)

#### Scenario: Position does not rebalance on brief out-of-range
- **WHEN** price exits the range for less than 180 seconds
- **THEN** the controller SHALL NOT issue a `StopExecutorAction`

#### Scenario: Position rebalances after sustained out-of-range
- **WHEN** price remains outside the range for 180+ seconds AND is 0.5%+ beyond the boundary
- **THEN** the controller SHALL issue a `StopExecutorAction` to trigger rebalancing

---

### Requirement: Price limits bracket monthly trading range
The config SHALL set price limits anchored to the observed monthly range (40,852–51,428 PUMP/SOL):

```
buy_price_min:   '40000'   # stop buying SOL if PUMP collapses
buy_price_max:   '50000'   # anchor for BUY positions
sell_price_min:  '45000'   # anchor for SELL positions
sell_price_max:  '56000'   # stop selling if PUMP moons
```

#### Scenario: KEEP fires when BUY position is anchored at buy_price_max
- **WHEN** a BUY position's upper bound equals `buy_price_max` (50,000) and price is above range
- **THEN** the controller SHALL KEEP the position and not rebalance further upward

#### Scenario: KEEP fires when SELL position is anchored at sell_price_min
- **WHEN** a SELL position's lower bound equals `sell_price_min` (45,000) and price is below range
- **THEN** the controller SHALL KEEP the position and not rebalance further downward
