## Context

Hummingbot already has `LPRebalancer` — a controller-executor architecture that automates CLMM position management. The gateway has full `raydium/clmm` support. The target pool (WSOL/PUMP, `45ssPkUQs1ssbeDqxD2mZrMdJYAXF7GyQyhS5xDXuWC5`) has real-validated metrics: $21.7M monthly volume, 150% monthly APR, 0.1% fee, tick spacing 10.

The operator's edge: **both tokens (SOL and PUMP) are acceptable long-term holds**, so impermanent loss is not a cost — it is portfolio rebalancing. Every fee earned is pure alpha on top of a directional hold.

**Resolved open questions:**

- **Trading pair name**: `resolve_trading_pair_from_pool()` in `gateway_lp.py` constructs the pair as `f"{base_symbol}-{quote_symbol}"` using the symbol from the token cache — no normalization. Expected result: `WSOL-PUMP`. Must be confirmed via gateway `pool-info` spike before deploying.
- **Candle availability**: No Raydium-specific candle feed exists in `CandlesFactory`. `LPRebalancer` itself does not use candles — it reads `current_price` from `executor.custom_info`. Volatility-adaptive width and momentum filter are therefore **not viable without significant additional infrastructure**, and have been dropped from v1 scope.

## Goals / Non-Goals

**Goals:**

- Automate LP rebalancing on the SOL-PUMP Raydium CLMM pool using two `LPRebalancer` controllers (narrow + wide) — no new controller code
- Dual-range strategy: narrow ±2% (70% capital, high fee density) + wide ±8% (30% capital, safety net)
- Fee auto-compounding via existing `_last_closed_`* rollover (built into `LPRebalancer`)
- Deploy ~$24 test / ~$1,320 full; `side=0` (BOTH), centered on current price
- Safe restart: `LPExecutor` adopts existing on-chain positions on redeploy — no duplicate positions opened

**Non-Goals:**

- New controller class — `LPRebalancer` is used directly via YAML config
- Volatility-adaptive range width — no Raydium candle feed available; dropped for v1
- Asymmetric range skew — dropped for v1
- Momentum filter — dropped for v1 (no candle data source for WSOL-PUMP)
- Gateway changes — `raydium/clmm` is production-ready as-is

## Decisions

### D1: Use `LPRebalancer` directly — no new controller

`LPRebalancer` with a YAML config is sufficient for v1. It handles executor lifecycle, KEEP logic, price limit anchoring, and fee rollover.

All the adaptive filter ideas (D2–D4 in the original design) required either a Raydium candle feed (which doesn't exist) or an in-process rolling price buffer (medium complexity, gap issues during rebalance). Neither is worth the complexity for a first deployment.

**Future path**: if adaptive width is desired later, the right data source is a rolling price buffer from `executor.custom_info["current_price"]` downsampled to 1-min buckets — but this is a separate change.

### D2: Dual-range strategy — narrow ±2% + wide ±8%

Single ±3% range was rejected: during a PUMP spike (10–20%/hr), the position goes OOR and earns zero fees while the rebalance is pending. A wide safety-net position fills this gap.

| | Narrow | Wide |
|---|---|---|
| `position_width_pct` | 4.0 (±2%) | 16.0 (±8%) |
| Capital share | 70% | 30% |
| Fee density | ~5–6× pool avg | ~1.5× pool avg |
| Expected rebalances | ~1/day | ~2–4/month |
| Role | Primary fee earner | Safety net during rebalance gap |

Wide position ensures at least 30% of capital earns fees even when narrow goes OOR and is rebalancing.

### D3: Rebalance timing — 5 min (narrow) / 15 min (wide)

- **Narrow**: `rebalance_seconds=300`, `rebalance_threshold_pct=0.5` — 5 min is enough to distinguish a wick from a trend; shorter than original 300s design confirmed adequate
- **Wide**: `rebalance_seconds=900`, `rebalance_threshold_pct=1.0` — wide range rarely exits, conservative timer avoids unnecessary gas on minor excursions

### D4: Price limits — tighter for narrow, wider for wide

Monthly range: 40,852–51,429 PUMP/SOL, current ~48,264.

**Narrow** (tighter bracket — stop chasing early):
```
buy_price_min:  38,000   # -7% below ATL
buy_price_max:  51,500   # just above ATH — anchor for BUY (KEEP)
sell_price_min: 44,000   # above ATL with buffer — anchor for SELL (KEEP)
sell_price_max: 56,000   # +9% above ATH
```

**Wide** (wider bracket — safety net should rarely hit limits):
```
buy_price_min:  32,000   # -22% below ATL — hard floor
buy_price_max:  55,000   # +7% above ATH — anchor for BUY (KEEP)
sell_price_min: 38,000   # -7% below ATL — anchor for SELL (KEEP)
sell_price_max: 65,000   # +26% above ATH
```

KEEP logic: once a BUY position is anchored at `buy_price_max`, no further upward rebalancing — position is optimally placed to catch pullback. Same logic on downside with `sell_price_min`.

### D6: Position adoption on restart — rank-based width matching

**Problem**: `LPExecutor` is a pure in-memory state machine. On restart, `active_executors` is empty; the controller creates new executors which open new positions on-chain, duplicating existing ones.

**Solution**: `LPExecutor.on_start()` calls `connector.get_user_positions(pool_address)` and adopts any existing position instead of creating a new one.

**Multi-position matching** (two controllers, same pool): positions are sorted by relative width `(upper-lower)/lower`. Each executor picks the position at the same rank as its own `config_width`. This is robust to any absolute width change — only the ordering (narrow < wide) must be preserved.

```
on-chain sorted by width:  [pos_A: 4%,  pos_B: 16%]
narrow executor config_width=4%  → rank=0 → pos_A ✓
wide   executor config_width=16% → rank=1 → pos_B ✓
```

⚠️ PnL tracking caveat: `initial_base_amount` / `initial_quote_amount` are set to current on-chain amounts (original deposit amounts are unknown after restart). PnL from the previous session is not carried over.

### D5: Fee auto-compounding — no additional mechanism needed

`LPRebalancer._last_closed_base_amount` and `_last_closed_quote_amount` already capture the full return from `removeLiquidity` — which on Raydium CLMM includes principal + accumulated fees in one step. Every rebalance is automatically a compound event.

## Risks / Trade-offs


| Risk                                                                                | Mitigation                                                                                                      |
| ----------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `raydium-sdk-v2` is still alpha (`v0.1.141-alpha`) — potential TX construction bugs | Start with $500, verify positions on Raydium UI, scale to $3,500 only after 48h stable operation                |
| PUMP volume collapse (meme loses attention)                                         | Monitor 7-day volume weekly; exit if 7d vol < $200k (currently $1.97M)                                          |
| Transaction failures during Solana congestion                                       | `LPExecutor` retry logic handles this (10 retries, user notification on max_retries_reached)                    |
| Price quote convention mismatch (`WSOL-PUMP` vs `SOL-PUMP`)is                       | Confirmed via gateway pool-info spike (task 1.1–1.2) before any capital deployed                                |
| ±3% too narrow during a sustained PUMP run                                          | KEEP logic parks BUY position at `buy_price_max` — no chasing; fee accumulation continues when price pulls back |


## Migration Plan

1. **Spike (Day 1)**: Call gateway `/connectors/raydium/clmm/pool-info` — confirm token symbols and `trading_pair` string
2. **Deploy $500 (Day 1–2)**: Create `conf/sol_pump_lp.yml`, run with `lp_rebalancer`, verify one full rebalance cycle on Raydium UI
3. **Scale (after 48h stable)**: Increase `total_amount_quote` to full allocation (~23 SOL at $150/SOL for $3,500)
4. **Rollback**: Stop controller → position closes automatically → full funds return to wallet; no residual on-chain state
