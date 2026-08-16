## 1. Range Box Model and Interaction

- [ ] 1.0 Read and follow `.github/skills/technical-indicator-drag-tools/SKILL.md` before adapting the PoC or the vendored DearCyGui reference.
- [ ] 1.1 Add an immutable source-space `ToolAnchor` and a minimal interactive-tool lifecycle contract with stable `tool_id`, semantic `tool_kind`, projection refresh, and disposal.
- [ ] 1.2 Add immutable box-specific geometry with finite-value validation and normalized bounds, composed from the common anchor vocabulary.
- [ ] 1.3 Add a package-owned `RangeBoxTool` implementing the lifecycle contract with visible drawing children and body/corner `DrawInvisibleButton` hit regions.
- [ ] 1.4 Implement move and corner-resize behavior from backup geometry plus cumulative plot-coordinate drag deltas.
- [ ] 1.5 Add source-to-plot projection, plot-to-source expansion, screen-space hit sizing, cursor feedback, and separate changing/committed geometry callbacks.
- [ ] 1.6 Route programmatic geometry mutation through the same validation, refresh, and committed-callback path.
- [ ] 1.7 Export the stable anchor, lifecycle, and range-box types from `dearcyfi`.
- [ ] 1.8 Expose semantic anchor roles and immutable current-anchor lookup for tooltip and future label consumers.

## 2. DearCyFi Ownership and Collapse Lifecycle

- [ ] 2.1 Add one chart-owned generic tool collection with stable-ID validation, read-only `tools` access, and filtered read-only `boxes` access.
- [ ] 2.2 Add callback-friendly `add_box(...)` with explicit geometry and candle/view-derived default geometry.
- [ ] 2.3 Add idempotent `remove_all_boxes()` that disposes drawing and interaction children.
- [ ] 2.4 Refresh every registered tool through the generic lifecycle after collapse, restore, and candle replacement without registering anchors as collapse-source series.
- [ ] 2.5 Define clear behavior for missing candles, invalid geometry, and boxes outside replacement candle ranges.
- [ ] 2.6 Add immutable box diagnostic snapshots and a callback-friendly `print_boxes()` command reporting stable IDs, canonical source geometry, and current plotted geometry.
- [ ] 2.7 Add one chart-managed anchor-tooltip coordinator with explicit active target ownership, plot-compatible parenting, owner-checked hover cleanup, and teardown before projection rebuild or disposal.
- [ ] 2.8 Add anchor-tooltip enablement and candle-style `dcg.Text` rows using chart-consistent source-date formatting and a basic numeric price format.

## 3. Demo Controls

- [ ] 3.1 Add a `Technical Analysis` collapsing header near the existing collapse controls.
- [ ] 3.2 Wire `Add Box`, `Print Boxes`, and `Remove All Boxes` controls directly to the chart operations.
- [ ] 3.3 Report add/remove outcomes through the existing demo status path without adding the controls to the data-widget registry.
- [ ] 3.4 Display printed box diagnostics through the existing status path and also emit them to the console.

## 4. Validation and Documentation

- [ ] 4.1 Add focused tests for anchor and geometry validation, move/resize updates, changing/committed callback phases, semantic anchor lookup, programmatic mutation, and disposal.
- [ ] 4.2 Add chart tests for stable identity, generic registration/refresh, filtered box access, add-many, diagnostic snapshots/output including the empty state, box-only remove-all idempotence, missing-candle errors, and current candle resolution.
- [ ] 4.3 Add collapse/restore/reload tests asserting canonical source anchors and rendered plot anchors remain coherent.
- [ ] 4.4 Add anchor-tooltip tests for canonical dates after collapse, current prices after movement, duplicate `GotHover`, target switching, stale `LostHover`, correct parent ownership, rebuild cleanup, and tool disposal.
- [ ] 4.5 Run the focused tests and the existing collapse, candle, econometric, and axis-assignment regression tests.
- [ ] 4.6 Run the demo and manually verify add, independent interaction, anchor coordinate tooltips before and after collapse, source/rendered coordinate printing, restore, and remove-all behavior.
- [ ] 4.7 Document the range-box API, source-time geometry semantics, callbacks, simple hover tooltips, and deferred Fibonacci/persistent-label/aggregation goals.
