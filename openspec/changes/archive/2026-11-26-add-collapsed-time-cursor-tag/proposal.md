# Change: Add Collapsed-Time Cursor Tag

## Why
DearCyGui's built-in plot mouse-position text displays the plotted X coordinate. After DearCyFi collapses time gaps, that coordinate is no longer the real market timestamp, so the corner readout shows an incorrect date and time.

## What Changes
- Add an optional X-axis cursor tag to `DearCyFi` that follows the mouse while it is over the plot.
- Convert the plotted X coordinate back to real time through the active gap map before formatting the tag text.
- Support selectable `DateTimeSpec` formatting and custom timestamp formatter callbacks for the cursor text.
- Use DearCyFi's existing local-time, 12/24-hour, and ISO-8601 settings with the built-in cursor formats.
- Color the tag green over bullish candles, red over bearish candles, and blue when the cursor is not over a candle, with configurable colors.
- Hide DearCyGui's built-in mouse-position text while the replacement cursor tag is enabled.
- Preserve direct timestamp formatting when the chart is not collapsed and define behavior over the synthetic interval retained between collapsed chunks.
- Add focused conversion/formatting tests and a manual hover validation path.

## Impact
- Affected specs: `collapsed-time-cursor-tag` (new)
- Depends on: the `time-collapse-coordination` capability introduced by `add-econometric-series-collapse-source`
- Affected code:
  - `src/dearcyfi/core.py`
  - `src/dearcyfi/DCG_Candle_Utils.py`
  - Tests under `tests/`
  - DearCyFi demo wiring or documentation used for manual interaction validation
- Compatibility: the replacement tag is configurable. Disabling it retains the caller's existing DearCyGui mouse-position configuration.