# Change: Add Series Y-Axis Assignment

## Why

Candles and econometric observations can have substantially different numeric ranges. Rendering both against `Y1` compresses one series and makes the combined chart difficult to read even though DearCyGui provides three independent Y axes.

## What Changes

- Add an explicit Y-axis argument to candle and econometric series construction, defaulting to `dcg.Axis.Y1` for backward compatibility.
- Keep every native element owned by a composite series on the selected axis, including candle volume, econometric markers, and econometric tooltip hit regions.
- Let `DearCyFi.set_data(...)` select the candle Y axis and preserve that assignment across data replacement.
- Reject non-Y axis values with a clear error while retaining `X1` as the shared time axis used by collapse coordination.
- Update the demo to render candles on `Y1` and weekly econometric data on an enabled, labeled, independently fitted `Y3` axis.
- Document that the optional label diagnostics continue to reserve `Y2` while enabled.

## Impact

- Affected specs: `series-axis-assignment` (new); depends on the pending `econometric-series` capability and existing `label-overlap-diagnostic` behavior
- Affected code: `src/dearcyfi/DCG_Candle_Utils.py`, `src/dearcyfi/econometric_series.py`, `src/dearcyfi/core.py`
- Affected demo: `examples/DearCyFi_Demo/DearCyFi_Demo.py`
- Affected tests and docs: candle/econometric unit tests, demo validation, and `README.md`
