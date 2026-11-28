## Context

The chart builds one map from the selected collapse source, normally the candles. Registered followers store original `source_dates` separately from their projected X coordinates. `project()` preserves elapsed offsets outside the source range, but the tick, date-context, and cursor formatters previously used `expand()`, which clamps exterior coordinates. Changing `expand()` globally would also change interactive tools.

## Decisions

### Invert the existing outer segments for axis display

Let `r_first` and `r_last` be the original source endpoints and `x_first` and `x_last` their collapsed coordinates. Resolve the real timestamp for a plotted coordinate `x` as follows:

| Plotted coordinate | Axis timestamp |
| --- | --- |
| `x < x_first` | `r_first + (x - x_first)` |
| `x_first <= x <= x_last` | Existing `expand(x)`, including bridge behavior |
| `x > x_last` | `r_last + (x - x_last)` |

These are the inverse branches of `project()` outside the source. If a follower observation was projected using either branch, its plotted X resolves back to its original timestamp, to floating-point precision. For example, with real offsets `[0, 10, 20, 100, 110]` and projected offsets `[0, 10, 20, 30, 40]`, a follower at real offset `125` plots at `55`; the axis conversion at `55` returns `125`, not `110`. Use the live map on every label refresh; when a source append reveals a gap, follower reprojection and the new map must agree.

### Format exterior positions normally

- Before the first source timestamp, the first segment's shift is zero. After the last source timestamp, the final segment's shift equals the total time removed by collapse. Neither side changes elapsed spacing or infers trading sessions, holidays, or unseen gaps.
- Keep existing tick placement, density, date/time format options, and spacing rules. Do not add a tick for every follower point or snap ticks to observations. The axis shows a timestamp at its selected precision; an observation tooltip remains the way to read a point's source date when no tick lands on it.
- Use the same axis-specific conversion for regular tick labels, date-context labels, and the cursor tag. Do not add a per-label marker or look up observations solely for formatting.

## Compatibility and scope

Custom cursor formatters receive the resolved timestamp and retain control over the complete tag string. The existing clamped conversion used by drawing tools stays separate so timestamp display does not change committed geometry.

Do not extend the collapse-source map with follower dates, change forward projection or retained bridges, or modify `expand()` defaults or drawing-tool behavior. No exchange calendar or new locator is needed. The pending [econometric display-shift proposal](../add-econometric-series-display-shift/proposal.md) addresses deliberately shifted positions: such positions must not be treated as exact observation anchors by virtue of having an original timestamp.
