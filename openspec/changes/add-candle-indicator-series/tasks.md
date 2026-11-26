## 1. Indicator calculation and management

- [ ] 1.1 Define the minimal candle-input, named-output, and indicator parameter contracts; support direct SMA use without demo dependencies.
- [ ] 1.2 Implement validated SMA period and OHLC selection, warm-up, non-finite windows, and observation-count gap semantics.
- [ ] 1.3 Add distinct stable indicator IDs and create/edit/remove lifecycle management, with a minimal GUI-facing type/parameter registry or factory.
- [ ] 1.4 Prepare and publish indicator changes with chart-owned candle full replacement, latest revision, and append, including generic candle mutation paths and rollback on failure.

## 2. Chart series and time coordination

- [ ] 2.1 Render each indicator instance as a single independently toggleable legend item; support source-date tooltips, Y-axis assignment, fitting, and missing-value line breaks.
- [ ] 2.2 Register and synchronize followers with the active collapse map, including creation while collapsed, non-candle collapse sources, and normal/gapped appends.
- [ ] 2.3 Preserve identity, hidden state, style, assigned axis, viewport, menu widgets, and coherent time state on updates and edits; clean up registrations, popup state, and callbacks on removal.

## 3. Demo controls

- [ ] 3.1 Add a left-side panel with indicator type, SMA period and OHLC field, Add, and actionable validation errors.
- [ ] 3.2 Add per-instance legend-menu Edit and Remove; implement a prefilled edit popup with Apply, Cancel, and error handling.
- [ ] 3.3 Integrate with synthetic streaming, candle reload and symbol changes without adding indicators to the comparison plot; retain the legend-identification probe.
- [ ] 3.4 Document the API, SMA definitions, limitations, and a manual demo walkthrough.

## 4. Verification

- [ ] 4.1 Test known SMA values for periods 1 and greater, warm-up, each OHLC field, insufficient data, non-finite values, gaps, and invalid parameters.
- [ ] 4.2 Test multiple independent instances, duplicate configurations, edits, cancellations, invalid edits, removal, and cleanup.
- [ ] 4.3 Test candle full replacement, repeated latest revisions and appends with and without gaps, generic mutation calls, and collapsed/uncollapsed operation; compare with full recomputation.
- [ ] 4.4 Test creation while collapsed, alternative collapse source, restore, source timestamps, Y axes, fit, legend visibility, tooltip lifetime, and menu persistence across redraws.
- [ ] 4.5 Inject calculation and publication failures for create/edit/candle mutations and verify prior coherent candle, indicator, map, presentation, and UI state.
- [ ] 4.6 Run targeted new and existing candle, econometric, streaming, collapse, axis, tooltip, and demo tests in the custom DearCyGui environment.
- [ ] 4.7 Run a rendered popup/legend interaction probe and record a manual demo walkthrough: add two SMAs, edit and remove one, stream revisions and a gap, collapse/restore, and reload.
- [ ] 4.8 Run `openspec validate add-candle-indicator-series --strict --no-interactive` and request review before implementation.
