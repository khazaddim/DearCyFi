## 1. Core Bar Rendering Migration

- [x] 1.1 Replace `core.py` horizontal overlay creation from `PlotHorizontalBars` to `dcg.PlotColorBars` with `horizontal=True` and `anchor="axis_max"`.
- [x] 1.2 Remove callback-based horizontal bar position updates tied to `AxesResizeHandler` for this feature.
- [x] 1.3 Preserve count-safe updates when X, Y, and colors lengths change.

## 2. Candle Volume Migration

- [x] 2.1 Replace internal candle volume `dcg.PlotDigital` with `dcg.PlotColorBars` in `PlotCandleStick`.
- [x] 2.2 Configure default volume geometry with `anchor="axis_min"`, `value_space="normalized"`, and `ignore_fit=True`.
- [x] 2.3 Normalize non-negative volume magnitudes to a stable range, including empty, zero, and all-zero inputs, so the maximum maps to the configured plot-height fraction.
- [x] 2.4 Derive default volume colors from candle direction (up/down) and keep `volume_kwargs` overrides.
- [x] 2.5 Keep volume series bound to the candle axis pair across construction, updates, and y-axis reassignment.
- [x] 2.6 Compare and tune normalized height and width defaults against the old `PlotDigital` appearance during pan and Y-axis zoom.

## 3. Legacy Utility Retirement

- [x] 3.1 Remove `DCG_Bar_Utils` imports from production paths.
- [x] 3.2 Keep `src/dearcyfi/DCG_Bar_Utils.py` as a deprecated compatibility module with guidance to use `dcg.PlotColorBars`.
- [x] 3.3 Update package exports/import sites if public surface changes.

## 4. Demo Integration

- [x] 4.1 Update DearCyFi demo bar-loading path to exercise the new horizontal PlotColorBars implementation.
- [x] 4.2 Add or align controls for normalized/data bar-length modes so behavior can be validated interactively.
- [x] 4.3 Confirm visible up/down candle-volume color distinction in demo.
- [x] 4.4 Confirm candle volume remains bottom-anchored with a stable screen-relative height while Y-axis limits change.
- [x] 4.5 Document that exact zoom-dependent horizontal sizing is deferred until volume-weighted price sampling work.

## 5. Validation And Documentation

- [x] 5.1 Add tests for bar count changes, per-bar color validation, and axis binding behavior.
- [x] 5.2 Add tests for candle volume color mapping against open/close direction.
- [x] 5.3 Add tests for volume normalization, zero/all-zero inputs, non-fit behavior, and stable screen-relative height under Y-axis zoom.
- [x] 5.4 Run existing label, date-context, and gap-collapse diagnostic tests unchanged as regression coverage.
- [x] 5.5 Document custom DearCyGui requirement, deprecated utility status, normalized volume behavior, and bar API behavior in README/demo docs.
- [x] 5.6 Run targeted tests and manual demo verification for pan/zoom smoothness and collapse interactions, accepting approximate first-stage horizontal sizing while comparing candle volume against the old `PlotDigital` appearance.
