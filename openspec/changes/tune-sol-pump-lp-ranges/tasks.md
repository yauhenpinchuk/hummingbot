## 1. Update Narrow Controller Config

- [x] 1.1 Set `position_width_pct: '5.5'` in `conf/controllers/sol_pump_lp_narrow.yml`
- [x] 1.2 Set `position_offset_pct: '0.4'` in `conf/controllers/sol_pump_lp_narrow.yml`
- [x] 1.3 Set `buy_price_max: '60000'` in `conf/controllers/sol_pump_lp_narrow.yml`
- [x] 1.4 Set `sell_price_max: '68000'` in `conf/controllers/sol_pump_lp_narrow.yml`
- [x] 1.5 Update YAML comments to reference stable-regime calibration (Oct 2025–Apr 2026 data)

## 2. Update Wide Controller Config

- [x] 2.1 Set `position_width_pct: '26.0'` in `conf/controllers/sol_pump_lp_wide.yml`
- [x] 2.2 Set `rebalance_seconds: 1800` in `conf/controllers/sol_pump_lp_wide.yml`
- [x] 2.3 Set `rebalance_threshold_pct: '1.5'` in `conf/controllers/sol_pump_lp_wide.yml`
- [x] 2.4 Set `buy_price_max: '70000'` in `conf/controllers/sol_pump_lp_wide.yml`
- [x] 2.5 Set `sell_price_max: '76000'` in `conf/controllers/sol_pump_lp_wide.yml`
- [x] 2.6 Update YAML comments to reference stable-regime calibration and new monthly range coverage

## 3. Verify and Deploy

- [x] 3.1 Verify both YAML files parse without errors (load with Python `yaml.safe_load` or hummingbot dry-run)
- [x] 3.2 Confirm no values were accidentally changed that shouldn't be (`buy_price_min`, `sell_price_min`, `rebalance_seconds` for narrow, `side`, `pool_address`, `total_amount_quote`)
- [ ] 3.3 Deploy updated configs (restart Hummingbot or wait for next hot-reload cycle)
- [ ] 3.4 Monitor first rebalance event for narrow controller — verify new range width (5.5%) opens correctly
- [ ] 3.5 Monitor first rebalance event for wide controller — verify new range width (26.0%) opens correctly
<!-- 3.3–3.5 require live Hummingbot instance; complete manually post-deploy -->
