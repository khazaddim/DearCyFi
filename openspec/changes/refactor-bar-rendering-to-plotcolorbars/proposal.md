# Change: Refactor Bar Rendering To PlotColorBars

## Why

DearCyFi still uses two legacy bar paths that do not take advantage of the custom DearCyGui branch in use on this repository:

- `DCG_Bar_Utils.PlotHorizontalBars` repositions `DrawRect` objects through a plot resize callback.
- `PlotCandleStick` volume uses `dcg.PlotDigital`, which does not provide per-bar fill colors for up/down state.

The custom DearCyGui implementation adds `dcg.PlotColorBars`, a native draw-loop series that resolves anchor position and normalized length inside the same plot render pass and supports one fill color per bar. Migrating to it should reduce callback-driven churn and enable smoother, richer bar rendering.

## What Changes

- Replace the horizontal-bar implementation used by `DearCyFi.load_horizontal_bars(...)` with `dcg.PlotColorBars(horizontal=True, anchor="axis_max")`.
- Remove callback-based horizontal bar repositioning from DearCyFi integration and retire `DCG_Bar_Utils.PlotHorizontalBars` from runtime usage.
- Replace candle volume `dcg.PlotDigital` usage in `PlotCandleStick` with `dcg.PlotColorBars` so bar colors can follow candle direction (green for up bars, red for down bars) with optional user override.
- Preserve label-extent, overlap, date-context, and gap-collapse diagnostics as-is, including their existing `dcg.PlotDigital` rendering where applicable.
- Keep axis-assignment behavior intact (`axes=(X1, selected_y_axis)`), including secondary-axis scenarios introduced by recent series-axis work.
- Update the DearCyFi demo controls/workflow so bar overlays and candle volume rendering exercise the new PlotColorBars path and expose normalization/anchor behavior where useful.
- Keep `DCG_Bar_Utils.py` as a deprecated compatibility module during this first-stage migration.
- Treat exact zoom-dependent sizing of price-sampled horizontal bars as deferred work until volume-weighted price sampling is designed and implemented.
- Add migration notes and compatibility constraints (custom DearCyGui required) to project documentation.

## Impact

- Affected specs: `color-bar-rendering` (new)
- Affected code:
  - `src/dearcyfi/DCG_Candle_Utils.py`
  - `src/dearcyfi/core.py`
  - `src/dearcyfi/DCG_Bar_Utils.py` (retired or compatibility shim)
  - `src/dearcyfi/__init__.py` (exports if needed)
- Affected demo:
  - `examples/DearCyFi_Demo/DearCyFi_Demo.py`
- Affected tests/docs:
  - candle and demo-facing tests
  - README usage notes for custom DearCyGui dependency and bar behavior
