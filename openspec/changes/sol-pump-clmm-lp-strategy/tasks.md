## 1. Spike — Verify Gateway and Pool

- [x] 1.1 Start the gateway locally and call `GET /connectors/raydium/clmm/pool-info` with `pool_address=45ssPkUQs1ssbeDqxD2mZrMdJYAXF7GyQyhS5xDXuWC5` — confirm pool loads, fee=0.1%, tick_spacing=10
      ✓ Confirmed: fee=0.1%, baseToken=So111...112, quoteToken=pumpC...Dfn, price=48391
- [x] 1.2 Record exact token symbol strings returned by gateway for WSOL and PUMP (determines `trading_pair` value in config — expected `WSOL-PUMP`)
      ✓ Confirmed: gateway token list uses "SOL" (not "WSOL") → trading_pair = SOL-PUMP
      ⚠️ Pitfall: pool-info response returns raw addresses, not symbols. Symbols come from conf/tokens/solana/mainnet-beta.json in the gateway.

## 2. Config

- [x] 2.1 Create `conf/sol_pump_lp.yml` with: `connector_name=raydium/clmm`, confirmed `trading_pair`, `pool_address`, `side=0` (BOTH), `position_width_pct=8.0`, `rebalance_seconds=600`, `rebalance_threshold_pct=0.5`, `position_offset_pct=0.3`, price limits `buy_price_min=36000`, `buy_price_max=51500`, `sell_price_min=44000`, `sell_price_max=58000`
      Created: `conf/controllers/sol_pump_lp_controller.yml` (controller config) + `conf/scripts/sol_pump_lp.yml` (script config)
      ⚠️ Pitfall: position_width_pct changed from 6.0→8.0 (±4%) after analysis — 24h pool spread is 4.1%, ±3% was too tight.
- [x] 2.2 Set `total_amount_quote` to SOL value of the test allocation (start with ~3.3 SOL ≈ $500)

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
