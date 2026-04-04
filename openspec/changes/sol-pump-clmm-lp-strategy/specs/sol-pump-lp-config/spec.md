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

### Requirement: Dual-controller capital allocation
The strategy SHALL run two `lp_rebalancer` controllers simultaneously — **narrow** and **wide** — sharing the same pool. Capital is split 70% / 30%:

| Controller | File | `total_amount_quote` (PUMP) | Test | Full |
|---|---|---|---|---|
| narrow | `sol_pump_lp_narrow.yml` | 70% | 10 000 | ~560 000 |
| wide   | `sol_pump_lp_wide.yml`   | 30% | 4 500  | ~240 000 |

- `side: 0` (BOTH-sided — operator holds both SOL and PUMP)
- `position_offset_pct: '0.3'` for narrow; `'0.5'` for wide

#### Scenario: Both controllers start and open separate positions
- **WHEN** both controllers start with no active executors
- **THEN** each SHALL open its own position in the pool at its own configured range

---

### Requirement: Narrow controller range and timing
`sol_pump_lp_narrow.yml` SHALL specify:
- `position_width_pct: '4.0'` (±2% — high fee density)
- `rebalance_seconds: 300` (5 min out-of-range before rebalancing)
- `rebalance_threshold_pct: '0.5'`

#### Scenario: Narrow position rebalances after 5 min OOR
- **WHEN** price remains outside the narrow range for 300+ seconds AND is 0.5%+ beyond the boundary
- **THEN** the narrow controller SHALL issue a `StopExecutorAction`

---

### Requirement: Wide controller range and timing
`sol_pump_lp_wide.yml` SHALL specify:
- `position_width_pct: '16.0'` (±8% — safety net, always covers narrow rebalance gap)
- `rebalance_seconds: 900` (15 min out-of-range before rebalancing)
- `rebalance_threshold_pct: '1.0'`

#### Scenario: Wide position does not rebalance on narrow rebalance event
- **WHEN** the narrow position goes OOR and rebalances
- **THEN** the wide position SHALL remain open (its range is wider and typically still in range)

---

### Requirement: Price limits bracket monthly trading range

**Narrow** (`position_width_pct: 4.0`, monthly range 40,852–51,429):
```
buy_price_min:  '38000'   # -7% below ATL
buy_price_max:  '51500'   # just above ATH
sell_price_min: '44000'   # above ATL with buffer
sell_price_max: '56000'   # +9% above ATH
```

**Wide** (`position_width_pct: 16.0`):
```
buy_price_min:  '32000'   # -22% below ATL — hard floor
buy_price_max:  '55000'   # +7% above ATH
sell_price_min: '38000'   # -7% below ATL
sell_price_max: '65000'   # +26% above ATH
```

#### Scenario: KEEP fires when BUY position is anchored at buy_price_max
- **WHEN** a BUY position's upper bound equals `buy_price_max` and price is above range
- **THEN** the controller SHALL KEEP the position and not rebalance further upward

#### Scenario: KEEP fires when SELL position is anchored at sell_price_min
- **WHEN** a SELL position's lower bound equals `sell_price_min` and price is below range
- **THEN** the controller SHALL KEEP the position and not rebalance further downward
