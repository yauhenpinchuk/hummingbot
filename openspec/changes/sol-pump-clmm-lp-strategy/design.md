## Context

Hummingbot already has `LPRebalancer` — a controller-executor architecture that automates CLMM position management. The gateway has full `raydium/clmm` support. The target pool (WSOL/PUMP, `45ssPkUQs1ssbeDqxD2mZrMdJYAXF7GyQyhS5xDXuWC5`) has real-validated metrics: $21.7M monthly volume, 150% monthly APR, 0.1% fee, tick spacing 10.

The operator's edge: **both tokens (SOL and PUMP) are acceptable long-term holds**, so impermanent loss is not a cost — it is portfolio rebalancing. Every fee earned is pure alpha on top of a directional hold.

**Resolved open questions:**

- **Trading pair name**: `resolve_trading_pair_from_pool()` in `gateway_lp.py` constructs the pair as `f"{base_symbol}-{quote_symbol}"` using the symbol from the token cache — no normalization. Expected result: `WSOL-PUMP`. Must be confirmed via gateway `pool-info` spike before deploying.
- **Candle availability**: No Raydium-specific candle feed exists in `CandlesFactory`. `LPRebalancer` itself does not use candles — it reads `current_price` from `executor.custom_info`. Volatility-adaptive width and momentum filter are therefore **not viable without significant additional infrastructure**, and have been dropped from v1 scope.

## Goals / Non-Goals

**Goals:**

- Automate LP rebalancing on the SOL-PUMP Raydium CLMM pool using `LPRebalancer` as-is — no new controller code
- Fixed ±3% range (`position_width_pct: 6.0`) selected from pool data analysis
- Fee auto-compounding via existing `_last_closed_`* rollover (built into `LPRebalancer`)
- Deploy $3,000–$4,000 with `side=0` (BOTH), centered on current price

**Non-Goals:**

- New controller class — `LPRebalancer` is used directly via YAML config
- Volatility-adaptive range width — no Raydium candle feed available; dropped for v1
- Asymmetric range skew — dropped for v1
- Momentum filter — dropped for v1 (no candle data source for WSOL-PUMP)
- Multi-position staggered ranges — future work
- Gateway changes — `raydium/clmm` is production-ready as-is

## Decisions

### D1: Use `LPRebalancer` directly — no new controller

`LPRebalancer` with a YAML config is sufficient for v1. It handles executor lifecycle, KEEP logic, price limit anchoring, and fee rollover.

All the adaptive filter ideas (D2–D4 in the original design) required either a Raydium candle feed (which doesn't exist) or an in-process rolling price buffer (medium complexity, gap issues during rebalance). Neither is worth the complexity for a first deployment.

**Future path**: if adaptive width is desired later, the right data source is a rolling price buffer from `executor.custom_info["current_price"]` downsampled to 1-min buckets — but this is a separate change.

### D2: Fixed range width of ±3% (`position_width_pct: 6.0`)

Derived from actual pool data:

- 24h observed spread: 3.1% → a ±3% range (total 6%) contains a full normal day with zero rebalances
- Monthly spread: 25.9% → wider ranges don't meaningfully reduce rebalances, they just reduce fee density

Fee density estimate at $3,500 capital:

```
Daily pool fees:          $154/day  (154,001 volume × 0.1%)
Your share (broad):       $3.05/day (1.98% of $173k TVL)
Concentration at ±3%:     ~4× multiplier → ~$12/day
Annual (conservative 50% in-range): ~$2,200/yr on $3,500 → ~63% APY
```

**±2% rejected**: highest fee density but PUMP spikes can be 10–20%/hour — too many rebalances during high-volume moments, which is exactly when fees are highest. Missing those minutes is costly.

**±5% rejected**: lower fee density, saves only trivial gas (Solana rebalance ≈ $0.15), not worth the trade-off.

### D3: Rebalance timing — 3 min wait, 0.5% threshold

`rebalance_seconds: 180` — shorter than the original 300s design. Reasoning: on a real pump, 3 min is enough to distinguish a wick from a trend. Waiting 5 min means more time fully OOR and earning zero fees.

`rebalance_threshold_pct: 0.5` — price must be 0.5% beyond the range boundary before the timer starts. Prevents the timer firing on noise at the range edge.

### D4: Price limits anchor at monthly range boundary

```
Pool monthly range: 40,852 – 51,428 PUMP/SOL

buy_price_min:   40,000   # stop buying SOL if PUMP collapses
buy_price_max:   50,000   # anchor BUY positions near monthly high
sell_price_min:  45,000   # anchor SELL positions near monthly low
sell_price_max:  56,000   # stop selling if PUMP moons hard
```

KEEP logic: once a BUY position is anchored at `buy_price_max` (50,000), no further upward rebalancing — the position is optimally placed to catch any pullback into range. Same logic on the downside with `sell_price_min`.

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
