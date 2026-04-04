## 1. Spike — Verify Gateway and Pool

- [x] 1.1 Start the gateway locally and call `GET /connectors/raydium/clmm/pool-info` with `pool_address=45ssPkUQs1ssbeDqxD2mZrMdJYAXF7GyQyhS5xDXuWC5` — confirm pool loads, fee=0.1%, tick_spacing=10
      ✓ Confirmed: fee=0.1%, baseToken=So111...112, quoteToken=pumpC...Dfn, price=48391
- [x] 1.2 Record exact token symbol strings returned by gateway for WSOL and PUMP (determines `trading_pair` value in config — expected `WSOL-PUMP`)
      ✓ Confirmed: gateway token list uses "SOL" (not "WSOL") → trading_pair = SOL-PUMP
      ⚠️ Pitfall: pool-info response returns raw addresses, not symbols. Symbols come from conf/tokens/solana/mainnet-beta.json in the gateway.

## 2. Config

- [x] 2.1 Create dual-controller config: `conf/scripts/sol_pump_lp.yml` referencing both `sol_pump_lp_narrow.yml` and `sol_pump_lp_wide.yml`
      - `sol_pump_lp_narrow.yml`: `position_width_pct=4.0`, `rebalance_seconds=300`, `rebalance_threshold_pct=0.5`, `position_offset_pct=0.3`, `total_amount_quote=10000` (test) / ~560000 (full, 70%)
      - `sol_pump_lp_wide.yml`:   `position_width_pct=16.0`, `rebalance_seconds=900`, `rebalance_threshold_pct=1.0`, `position_offset_pct=0.5`, `total_amount_quote=4500` (test) / ~240000 (full, 30%)
      ⚠️ Pitfall: both controllers share the same `pool_address` — position adoption on restart must use rank-based matching (see task 2.3)
- [x] 2.2 Set `total_amount_quote` to test allocation (narrow=10000 PUMP ~$16.5, wide=4500 PUMP ~$7.5)
- [x] 2.3 Fix `LPExecutor.on_start()` to adopt existing on-chain positions on restart
      Implemented `_adopt_existing_position_if_any()` in `hummingbot/strategy_v2/executors/lp_executor/lp_executor.py`
      Uses `connector.get_user_positions(pool_address=...)` and rank-based width matching: sort positions by width, pick the one at the same rank as this executor's `config_width = (upper-lower)/lower`
      ⚠️ Pitfall: `min(abs(width - config_width))` matching breaks when config widths are updated — rank-based matching is robust to any value change as long as narrow_config < wide_onchain

## 3. Deploy and Validate

- [ ] 3.1 Start gateway + hummingbot with `start --script v2_with_controllers.py --conf sol_pump_lp.yml`
      ⚠️ Manual step — run inside the hummingbot CLI after gateway is up
- [ ] 3.2 Verify position opens on Raydium UI at the correct ±3% range around current price
- [ ] 3.3 Observe one full rebalance cycle: position goes OOR → timer fires after 3 min → position closes and reopens — confirm new bounds are correct
- [ ] 3.4 Confirm fee rollover: new position size ≥ original (fees included in closed amounts)
- [ ] 3.5 Check KEEP logic fires: if price moves past `buy_price_max` or `sell_price_min`, confirm controller holds position rather than chasing

## 4. Scale-Up

- [ ] 4.1 After 48h stable operation with no unexpected failures, update `total_amount_quote` to full allocation (~23 SOL for $3,500 at $150/SOL)
- [ ] 4.2 Monitor 7-day volume weekly — exit strategy if 7d pool volume drops below $200k
