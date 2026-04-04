## Context

The SOL-PUMP Raydium CLMM LP strategy runs two simultaneous positions — narrow (70% capital) and wide (30% capital) — via the `lp_rebalancer` controller. All parameters are declared in two YAML config files; the controller reads them and manages positions automatically. No controller logic changes are needed.

The parameter changes are grounded in 265 days of daily close data (CoinGecko: `solana` + `pump-fun`, Jul 14 2025–Apr 4 2026). The data was computed as a ratio: `SOL_USD / PUMP_USD` = PUMP per SOL (the pair's native price). Key statistics used:

| Metric | Value |
|--------|-------|
| All-time low | 24,076 (Jul 16, 2025) |
| All-time high | 74,845 (Jul 29, 2025) |
| Current price | 48,481 (= p52, near median) |
| p10 / p25 / p50 / p75 / p90 | 37,231 / 41,308 / 46,869 / 52,975 / 63,675 |
| Avg daily move (all data) | 4.46% |
| Avg daily move (stable regime: Oct 2025+) | ~3.1% |
| Median monthly range | 48.4% (all); ~25% (stable regime) |

Live pool data from Raydium API (Apr 4 2026):

| Metric | Value |
|--------|-------|
| Pool fee rate | 0.1% |
| TVL | $162,642 |
| Volume 24h | $140,703 |
| Volume 30d | $17,495,476 |
| Base fee APR 7d | 35.0% |
| Base fee APR 30d | 129.1% |

The 30d vs 7d APR gap (129% vs 35%) reflects high volume in Jan 2026 (price dropped 47% that month) followed by a calmer Mar/Apr period. The pool has very high volume-to-TVL ratio (~86% daily turnover at current pace), which makes concentrated LP positions exceptionally profitable relative to larger pools.

Two regimes were identified:
- **Launch spike** (Jul–Sep 2025): price swung 3× in 6 weeks; daily moves ~6%; not representative of ongoing behavior.
- **Stable regime** (Oct 2025–present): price range ~37k–65k; daily moves ~3%; monthly range ~25%.

The previous config was based on a single 30-day snapshot from the launch era, which inflated volatility assumptions and led to an overly tight narrow range and an insufficiently wide safety net.

## Goals / Non-Goals

**Goals:**
- Increase narrow range width so the position stays in-range a meaningful portion of the time (target: ~45–50% vs. current 31%)
- Increase wide range width so it genuinely covers a median monthly move without rebalancing (target: ~87% in-range vs. current 75%)
- Raise the upper price limits to stop capping the buy-side at a price only 7% above current market
- Slow the wide controller's rebalance trigger to reduce unnecessary repositioning

**Non-Goals:**
- Changing the dual-position architecture (narrow + wide split remains)
- Changing capital allocation percentages (70/30 remains)
- Modifying controller logic or the `lp_rebalancer` Python code
- Optimizing for the launch-era volatile regime (Jul–Sep 2025 data excluded from calibration as unrepresentative)

## Decisions

### Decision 1: Use stable-regime data as the calibration baseline

**Chosen**: Calibrate widths and limits on Oct 2025–Apr 2026 data only.

**Rationale**: The Jul–Sep 2025 launch spike is a one-time event caused by the PUMP token's initial price discovery. Its daily moves (~6%) and monthly ranges (~80%) are approximately 2× the stable-regime values. Using this data would force us to either widen positions to unproductive levels or accept the same in-range rate we already have. The asset has 6+ months of post-stabilization history — that is a sufficient calibration window.

**Alternative considered**: Equal-weight all 265 days. Rejected because it inflates volatility by 40–50% and designs the strategy for a regime that is unlikely to recur at the same intensity.

**Risk**: If PUMP undergoes another high-volatility episode (e.g., on a new exchange listing or major market event), the narrower-relative-to-launch ranges will rebalance more frequently. This is an acceptable operational risk; the system handles rebalancing automatically.

---

### Decision 2: Narrow width 4.0% → 5.5%

**Chosen**: `position_width_pct: '5.5'` (±2.75%)

**Rationale**:
- Stable-regime avg daily move ≈ 3.1%. A 5.5% width catches a typical day within the range.
- 3-month backtest (Jan–Apr 2026, $10k capital, per-day volume estimates):

  | Config | In-range | Rebalances | Conc. factor | Net conc. (conc × IR%) |
  |--------|----------|-----------|--------------|----------------------|
  | 4.0% (current) | 40% | 50 | 50.5x | 20.2x |
  | 5.5% (proposed) | 50% | 40 | 36.9x | 18.5x |

- **Critical finding**: the fee trade-off inverts in volatile months. In January 2026 (47% price range), the 4% position was in-range only **19%** of the time vs **35%** for the 5.5% position. Net effective concentration: `19% × 50.5x = 9.6x` (current) vs `35% × 36.9x = 12.9x` (proposed). The proposed earns **+34% more fees in the most volatile month**.
- In calm months (Feb/Mar, 20–25% range), the current config slightly outperforms due to its higher concentration when both positions stay in-range. The overall 3-month net fee difference is ~10% in favour of the current config, but this gap is driven by the calmer months and partially reverses when volatility picks up.
- 5.5% vs. 4.0%: 27% lower concentration factor, offset by 25% more time in-range. The net result is near fee-neutral while meaningfully reducing rebalance frequency (50 → 40 over 3 months).

**Alternative considered**: 6.0%. Provides better in-range (similar to 5.5% in calm months, better in volatile months) at slightly lower concentration. Acceptable alternative; 5.5% chosen as a more conservative step — can revisit if daily moves remain below 3%.

---

### Decision 3: Wide width 16.0% → 26.0%

**Chosen**: `position_width_pct: '26.0'` (±13%)

**Rationale**:
- Stable-regime median monthly range ≈ 25%. A 26% wide position covers the median month without rebalancing.
- Simulation: 16% → 75% in-range; 20% → 83%; 30% → 89%. The 26% estimate puts us at ~87% in-range.
- The "safety net" purpose (catch the price when the narrow position rebalances) is better served by a position that moves only ~1–2×/month rather than ~7×/month (current 65 rebalances / 9 months).
- Lower concentration is fine for the wide position: it holds only 30% of capital and serves a protective role rather than a fee-maximization role.

**Alternative considered**: 20% (more conservative). Gives 83% in-range but still gets hit by the ~17% of months with moves >20%. With 26% we cover the median well; the tail months (>26% range, i.e., ~20% of months) are the exception.

---

### Decision 4: Raise upper price limits

**Chosen**:
- Narrow `buy_price_max`: `51,500` → `60,000`
- Narrow `sell_price_max`: `56,000` → `68,000`
- Wide `buy_price_max`: `55,000` → `70,000`
- Wide `sell_price_max`: `65,000` → `76,000`

**Rationale**: Current price is ~48,481. The previous `buy_price_max` for narrow (51,500) is only ~6.2% above current price — the BUY-side KEEP logic fires immediately on any modest rally, preventing the strategy from following upward price movement. **Backtest confirms this is the highest-impact fix in this change**: the narrow position was capped during most of January 2026 (price ranged 40k–65k), meaning the KEEP anchor prevented proper rebalancing for days at a time. With `buy_price_max: 60,000`, the KEEP only triggers if price is ~24% above current — matching the stable-regime p80 level. The new values are grounded in historical percentiles (p80–p99) rather than ATH + small buffer.

**Floor limits preserved**: `buy_price_min` (38,000 narrow / 32,000 wide) and `sell_price_min` (44,000 narrow / 38,000 wide) remain unchanged. These are the conservative downside safety stops; p10 = 37,231 and p5 = 33,914 support the existing floor values.

---

### Decision 5: Slow the wide controller trigger

**Chosen**: `rebalance_seconds: 1800`, `rebalance_threshold_pct: '1.5'`

**Rationale**: With a 26% wide position, the price must move ~13% from entry to exit the range. When this happens, it's a significant regime shift, not noise. Waiting 30 minutes (vs. 15) and requiring 1.5% beyond the boundary (vs. 1.0%) ensures we don't rebalance on brief price spikes that would snap back. The narrow controller is unaffected (300s / 0.5% stays — appropriate for its tighter range).

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| New wide range still not wide enough during a repeat of the Jul 2025 spike (80%+ monthly range) | Backtest shows wide position at 26% was 84% in-range even in January (47% range month). Price limits act as additional circuit breakers (KEEP at 76,000 = ATH+2%). |
| Increasing narrow width reduces fee concentration by ~27% per tick | Backtest invalidates this as a simple trade-off: proposed earns +34% more fees than current in volatile months (net conc 12.9x vs 9.6x in Jan 2026). Calm-month fee edge for current config is ~10% but volatile months flip it. Net 3-month fee difference: ~-10% in favour of current (calm period dominated). |
| Volume decay — pool volume has dropped from ~$290k/day (Jan) to ~$140k/day (current) | APR scales linearly with volume. Even at current 7d volume pace, both strategies yield well above DeFi benchmarks. APR sensitivity at various TVL levels: $163k→600%+, $488k→200%+, $813k→115%+. Strategy remains viable unless TVL grows 10x without matching volume growth. |
| Stable regime may not persist | If daily moves increase back above 5%, both configurations will rebalance more frequently, but proposed would again perform relatively better (as shown in January). Monitor 30-day rolling volatility; if it exceeds 5% avg daily move for 14 consecutive days, revisit widths. |
| Existing positions don't auto-resize | Positions migrate to new widths naturally on the next out-of-range event. No manual close needed, but there is a transition window where old-width positions are still open. |

## Migration Plan

1. Update YAML files (`sol_pump_lp_narrow.yml`, `sol_pump_lp_wide.yml`)
2. Restart the Hummingbot instance (or hot-reload if controller supports it — `lp_rebalancer` reads config on each rebalance cycle, so the new widths take effect on the next rebalance without a restart)
3. Monitor first 2 rebalance events for each controller to verify the new ranges open correctly
4. No rollback script needed — reverting means restoring old YAML values and waiting for next rebalance cycle

**Rollback**: restore previous YAML values from git; next rebalance cycle applies old parameters.

## Open Questions

1. **Is the stable-regime daily move continuing to decline?** Mar–Apr 2026 avg daily move ~2.8%. If this persists, 5.5% remains slightly oversized and 6.0% becomes viable. Schedule a re-review in July 2026.

2. **Volume decay trajectory.** Pool volume has declined significantly: ~$9M estimated in Jan, ~$2.5M in March, ~$600k current pace in April. If this trend continues to ~$1M/month, the base APR (at current TVL) drops to ~7%, reducing net strategy APR to ~50–80% — still good, but materially different from current projections. Track monthly volume against TVL to monitor this.

3. **Does the `lp_rebalancer` hot-reload config on each cycle?** If it caches config at startup, a restart is required after YAML update.

4. **IL accuracy.** The backtest models IL only at the moment of rebalance (≈$200 on $10k over 3 months, ~2%). Actual IL accumulates continuously within-range as price drifts. True IL may be 2–5× higher. Even at 5× ($1,000), it's less than 7% of estimated fee income — does not change the decision, but worth monitoring in production.
