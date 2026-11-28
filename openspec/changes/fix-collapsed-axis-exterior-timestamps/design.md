## Context

The chart builds one map from the selected collapse source, normally the candles. Registered followers store original `source_dates` separately from their projected X coordinates. `project()` preserves elapsed offsets outside the source range, but the regular tick and date-context formatters both call `expand()`, which clamps exterior coordinates. Changing `expand()` globally would also change cursor tags and interactive tools.

## Decisions

### Invert the existing outer segments for axis display

Let `r_first` and `r_last` be the original source endpoints and `x_first` and `x_last` their collapsed coordinates. Resolve the real timestamp for a plotted coordinate `x` as follows:

| Plotted coordinate | Axis timestamp |
| --- | --- |
| `x < x_first` | `r_first + (x - x_first)` |
| `x_first <= x <= x_last` | Existing `expand(x)`, including bridge behavior |
| `x > x_last` | `r_last + (x - x_last)` |

These are the inverse branches of `project()` outside the source. If a follower observation was projected using either branch, its plotted X resolves back to its original timestamp, to floating-point precision. For example, with real offsets `[0, 10, 20, 100, 110]` and projected offsets `[0, 10, 20, 30, 40]`, a follower at real offset `125` plots at `55`; the axis conversion at `55` returns `125`, not `110`. Use the live map on every label refresh; when a source append reveals a gap, follower reprojection and the new map must agree.

### Distinguish exact observations from empty chart space

- An exterior tick that coincides with a registered follower's unshifted projected observation can display the corresponding original timestamp without an extrapolation marker. Match the actual coordinate within floating-point precision, not by nearest observation, pixel distance, or matching formatted text. If several followers share that exterior coordinate under the shared projection, their timestamps agree to that precision.
- Mark other exterior labels with `~` and document that it means the chart continues the nearest endpoint at one elapsed second per axis second. No trading sessions, holidays, or unseen gaps are inferred. Apply the distinction consistently to regular labels and date-context repairs; do not use the marker in date-suffix comparisons or let duplicate suppression remove a needed distinction between observed and extrapolated labels.
- Keep existing tick placement, density, date/time format options, and spacing rules. Do not add a tick for every follower point or snap ticks to observations. The axis shows a timestamp at its selected precision; an observation tooltip remains the way to read a point's source date when no tick lands on it.
- Use one axis-specific conversion for both formatting paths. Keep the coordinate conversion independent of series registration; observation matching determines the label qualification, not the timestamp. Avoid a per-tick full scan of series data or copying full source arrays on pan and zoom.

## Compatibility and scope

Do not extend the collapse-source map with follower dates, change forward projection or retained bridges, or modify `expand()` defaults, cursor tags, or drawing-tool behavior. No exchange calendar or new locator is needed. The pending [econometric display-shift proposal](../add-econometric-series-display-shift/proposal.md) addresses deliberately shifted positions: such positions must not be treated as exact observation anchors by virtue of having an original timestamp.
