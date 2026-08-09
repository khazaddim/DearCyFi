## 1. Core Bar Rendering Migration

- [ ] 1.1 Replace `core.py` horizontal overlay creation from `PlotHorizontalBars` to `dcg.PlotColorBars` with `horizontal=True` and `anchor="axis_max"`.
- [ ] 1.2 Remove callback-based horizontal bar position updates tied to `AxesResizeHandler` for this feature.
- [ ] 1.3 Preserve count-safe updates when X, Y, and colors lengths change.

## 2. Candle Volume Migration

- [ ] 2.1 Replace internal candle volume `dcg.PlotDigital` with `dcg.PlotColorBars` in `PlotCandleStick`.
- [ ] 2.2 Derive default volume colors from candle direction (up/down) and keep `volume_kwargs` overrides.
- [ ] 2.3 Keep volume series bound to the candle axis pair across construction, updates, and y-axis reassignment.

## 3. Legacy Utility Retirement

- [ ] 3.1 Remove `DCG_Bar_Utils` imports from production paths.
- [ ] 3.2 Decide and implement either deletion or deprecation shim for `src/dearcyfi/DCG_Bar_Utils.py`.
- [ ] 3.3 Update package exports/import sites if public surface changes.

## 4. Demo Integration

- [ ] 4.1 Update DearCyFi demo bar-loading path to exercise the new horizontal PlotColorBars implementation.
- [ ] 4.2 Add or align controls for normalized/data bar-length modes so behavior can be validated interactively.
- [ ] 4.3 Confirm visible up/down candle-volume color distinction in demo.

## 5. Validation And Documentation

- [ ] 5.1 Add tests for bar count changes, per-bar color validation, and axis binding behavior.
- [ ] 5.2 Add tests for candle volume color mapping against open/close direction.
- [ ] 5.3 Document custom DearCyGui requirement and bar API behavior in README/demo docs.
- [ ] 5.4 Run targeted tests and manual demo verification for pan/zoom smoothness and collapse interactions.
