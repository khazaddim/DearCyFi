## 1. Shared streaming contract
- [ ] 1.1 Add shared finite timestamp, cached median-interval, boundary-tolerance, and latest-occupancy logic, retaining floating-point seconds.
- [ ] 1.2 Add chart-managed generic check/append/latest-update operations and an optional mutation adapter capability without breaking projection-only registrations.
- [ ] 1.3 Implement candle and scalar econometric adapters and candle convenience methods, keeping chart caches, indexes, annotations, volume, and source/plot arrays consistent.
- [ ] 1.4 Validate complete proposed state before publishing; preserve the prior coherent chart state on rejected input or application failure.

## 2. Incremental timeline coordination
- [ ] 2.1 Extend gap-manager state and map-tail/index/date-anchor maintenance for normal and irregular-gapped source appends without steady-state history scans or median recalculation.
- [ ] 2.2 Retain equivalent incremental metadata while uncollapsed and ensure subsequent collapse/restore uses the same accepted cadence and gap history.
- [ ] 2.3 Reproject affected follower suffixes under their existing policies and refresh tool projections, labels, cursor mapping, and chart caches without changing canonical source data.
- [ ] 2.4 Preserve selected source, collapse state, visibility, styles, Y-axis, and viewport; wake rendering after successful mutation.

## 3. Focused verification
- [ ] 3.1 Test occupancy and returned timestamps, including five-minute 10:00/10:03/10:05 cases, boundary epsilon, realistic epoch float precision, invalid timestamps, empty/singleton data, and unknown IDs.
- [ ] 3.2 Test independent partial OHLCV replacement, replacement volume semantics, invalid resulting candles, no-op update rejection, duplicate/out-of-order appends, daily/four-hour rejection, and daily/two-day plus non-integral longer-gap acceptance.
- [ ] 3.3 Test candle and econometric streaming as source and follower in collapsed and uncollapsed modes, projection-only registration compatibility, and full-replacement cadence reset.
- [ ] 3.3.1 Cover the complete spacing/state matrix: below median rejects in either mode, equal spacing removes no additional time, and above median removes only excess time when collapsed; verify uncollapsed appends leave follower/tool projections untouched.
- [ ] 3.4 Test liquidity follower points before/inside/after a new gap with both projection policies, future-shifted points, tool anchors, collapse/restore, and date boundaries.
- [ ] 3.5 Instrument steady-state append to prove it does not invoke full gap builders, rescan historical source timestamps, or recompute median spacing; verify unchanged follower prefixes are reused.
- [ ] 3.6 Inject preparation and publication failures and verify data/map/presentation coherence; cover hidden series, assigned axes, volume, and tooltip source dates.
- [ ] 3.7 Run targeted existing gap-projection, collapse-coordination, candle/econometric, axis, cursor-tag, and tool suites plus the new focused tests using the workspace's custom DearCyGui environment.

## 4. Documentation and approval
- [ ] 4.1 Document public signatures, return shapes, seconds/interval-start semantics, tolerance formula, errors, cadence lifecycle, and a provider-neutral serialized async-consumer example in README.
- [ ] 4.2 Document deferred initial bulk collection, broker adapters, historical correction, calendar policies, and rendering optimizations.
- [ ] 4.3 Validate the implemented change with `openspec validate add-incremental-series-streaming --strict --no-interactive` and request review.
