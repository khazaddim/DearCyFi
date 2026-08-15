## Context

`DearCyFi` renders time-collapsed data in synthetic X coordinates. Its resize callback already calls `GapCollapsedTimeMap.expand()` to convert those coordinates back to real timestamps for tick labels, but DearCyGui's built-in mouse-position text formats the synthetic coordinate directly.

DearCyGui provides the two UI primitives needed for a replacement: an `AxisTag` attached to `X1`, and plot-owned mouse and hover handlers. The plot's `no_mouse_pos` property suppresses the built-in corner readout.

## Goals / Non-Goals

- Goals:
  - Display the real timestamp corresponding to the mouse's plotted X coordinate.
  - Keep the tag positioned at the mouse's plotted coordinate.
  - Provide built-in and application-defined cursor timestamp formats.
  - Match DearCyFi's existing timezone and clock-format settings for built-in formats.
  - Communicate bullish, bearish, or no-candle context through tag color.
  - Avoid per-move gap detection or map reconstruction.
- Non-Goals:
  - Replacing the built-in Y-coordinate readout.
  - Changing gap-collapse or `expand()` semantics.
  - Snapping the cursor to a candle or follower-series observation.
  - Adding a crosshair or a general-purpose data tooltip.

## Decisions

### Own the feature in `DearCyFi`

The plot class will create and manage one `AxisTag` under `X1` because it owns the active gap map, time-format settings, axis, and handlers. The feature will be exposed through a constructor option and the tag will remain accessible for host-level styling.

### Separate plotted position from displayed timestamp

On mouse movement, the tag coordinate will remain `X1.mouse_coord`. Its text will be generated from:

- the same coordinate directly when time is not collapsed; or
- `GapCollapsedTimeMap.expand(X1.mouse_coord)` when a map is active.

This distinction keeps the tag under the pointer while displaying real time.

### Support built-in format specs and custom formatters

The cursor configuration will accept either a `locator_time3.DateTimeSpec` or a callable receiving the expanded real Unix timestamp and returning text. A default date-and-time spec will provide the out-of-box format. `DateTimeSpec` values will use `locator_time3.format_datetime()` with the plot's existing local-time, 12/24-hour, and ISO-8601 settings; custom callables own their complete output. Conversion and formatting will live in a small method that can be tested without synthesizing mouse events.

Invalid formatter types will fail during configuration, and a custom callable that does not return a string will raise a clear error rather than assigning an invalid value to `AxisTag.text`.

### Let the candle renderer own candle hit lookup

`PlotCandleStick` already owns plotted candle dates, body width, open/close direction, and configured bull/bear colors. It will expose a focused X-coordinate query that returns the rendered candle color when the coordinate falls within a candle body's horizontal bounds and `None` otherwise. If unusual candle weights produce overlapping bounds, the nearest candle center wins.

The cursor callback will use this plotted-coordinate query after updating the tag position. A returned bullish color produces the configured bullish tag color (green by default), a bearish color produces the configured bearish tag color (red by default), and no match produces the configurable no-candle color (blue by default). Equality follows existing rendering behavior: `close >= open` is bullish.

The lookup remains correct after collapse because `PlotCandleStick.dates` contains the currently rendered coordinates while its source dates remain separate. Empty candle data, charts containing only non-candle series, and positions between candle bodies all select blue.

### Replace the built-in readout only while enabled

When the cursor tag is enabled, the plot will set `no_mouse_pos` so DearCyGui does not also render the incorrect corner value. When the feature is disabled, DearCyFi will not override the caller's mouse-position configuration. The replacement intentionally supplies only the corrected X timestamp; replacing the Y readout is outside this change.

### Follow existing inverse-map boundary behavior

The short synthetic interval retained between collapsed chunks has no unique real timestamp. The cursor will use the existing `expand()` result, matching DearCyFi's repaired tick labels: positions in the bridge resolve to the previous retained boundary until the next chunk boundary is reached.

## Risks / Trade-offs

- Hiding DearCyGui's built-in readout also removes its Y value. This is explicit and limited to configurations that enable the replacement tag.
- Updating tag text and color on every mouse move adds callback work. The operation is one map lookup, one candle-coordinate lookup, and formatting; it does not rebuild the gap map or candle drawings.
- A linear candle lookup would scale poorly for large datasets. The implementation will use sorted plotted candle centers and a nearest-index search, then test only the neighboring candidate bounds.
- A permanently visible tag could remain at a stale coordinate after the pointer leaves. Plot hover enter/leave handlers will control visibility, and non-finite mouse coordinates will also hide it.

## Migration Plan

Add the configurable feature to `DearCyFi` without changing collapse-map data structures. Consumers that prefer DearCyGui's original corner display can disable the cursor tag. Removing the feature requires only removing its tag and handlers; collapse behavior remains unchanged.