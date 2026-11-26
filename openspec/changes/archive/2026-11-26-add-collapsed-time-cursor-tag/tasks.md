## 1. Cursor Time Conversion

- [x] 1.1 Add a focused `DearCyFi` method that converts a plotted X coordinate to real time through the active gap map and formats it with either a configured `DateTimeSpec` or custom formatter callable.
- [x] 1.2 Validate formatter configuration and custom formatter return values with clear errors.
- [x] 1.3 Cover built-in format variants, custom formatting, direct, collapsed, restored, non-finite, and synthetic bridge-coordinate behavior with deterministic tests.

## 2. Candle Color Lookup

- [x] 2.1 Add a focused `PlotCandleStick` query using a semantic band equal to half the median rendered candle spacing on each side, with nearest-center resolution for overlapping bounds.
- [x] 2.2 Return the renderer's bullish or bearish classification/color for a matching candle and no match outside the series bands.
- [x] 2.3 Test bullish, bearish, equal open/close, midpoint, outside-band, empty-data, collapsed-coordinate, and overlapping-band cases.

## 3. Axis Tag Interaction

- [x] 3.1 Add a constructor option and create one initially hidden `dcg.AxisTag` under `X1` when the feature is enabled.
- [x] 3.2 Add configurable bullish, bearish, and no-candle tag colors defaulting to green, red, and blue.
- [x] 3.3 Add a plot-owned mouse-move callback that updates tag coordinate, formatted text, and candle-aware color without mutating series or tick data.
- [x] 3.4 Add hover enter/leave behavior and hide the tag for invalid mouse coordinates.
- [x] 3.5 Suppress DearCyGui's built-in mouse-position text while the replacement tag is enabled without overriding caller configuration when disabled.
- [x] 3.6 Expose the managed tag and semantic color configuration for host-level customization.

## 4. Validation

Until CI is configured with the required custom DearCyGui build, run validation with the repository's `.venv-dcg` environment rather than the default `.venv` environment.

- [x] 4.1 Using `.venv-dcg`, run the focused automated tests for cursor conversion, formatting, candle color lookup, and existing time-collapse regression tests.
- [X] 4.2 Using `.venv-dcg`, manually verify in the DearCyFi demo that the tag follows the pointer before and after collapse, displays each configured timestamp format, changes green/red/blue with candle context, disappears outside the plot, and does not duplicate the stock corner readout.