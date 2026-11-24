## Context

The chart builds a historical map from the selected source's actual timestamps. Registered followers keep their source timestamps and receive projected plot coordinates. Streaming can extend the map and reproject affected followers. Beyond the latest source point, projection uses the final known offset, while inverse expansion currently clamps to the source endpoint.

The intended first use is a weekly liquidity signal shown alongside weekly, daily, or minute candles. Its lead is an approximate exploratory alignment, not an assertion that the signal predicts a particular price or date.

## Decisions

### Separate shifts

- Maintain independently editable collapsed and uncollapsed display shifts per econometric series; positive moves right, negative moves left, and zero retains existing behavior.
- Accept collapsed source-candle interval counts and approximate calendar weeks as input. Specify the conversion to collapsed-axis coordinates using the selected source's historical data; do not treat a calendar week as seven uncompressed plot days.
- Initialize the uncollapsed shift once from the average compression over the loaded candle history, expressed in real-time units. Once initialized, it can be adjusted independently; streaming and toggling collapse must not silently overwrite an explicit setting.
- Preserve the original observation timestamps and values. The shift is a display transform, applied after the current mode's projection, not a resampling or modification of the underlying data.
- Reject or explicitly report unavailable conversions when there is insufficient usable source history; do not silently invent a cadence or compression ratio.

### Coordination

The chart and series need a single, documented ownership model for base projected coordinates and the display shift. Collapse, restore, source selection, streaming appends and revisions, follower reprojection, and error recovery must not lose or apply the shift twice. A source change or data reload must not silently reinterpret an existing shift against a different cadence.

The chart's original source timestamps remain the basis for gap detection, streaming and tooltips. A shifted series must not become an alternative source of historical gaps merely because it extends into the future.

### Historical compression uncertainty

Use the observed distribution of time removed during historical candle-gap collapse as the basis for an estimated horizontal range on shifted future observations. Make clear that this is a timing approximation based on historical gaps, not a liquidity forecast interval or probability of market performance.

The estimator is intentionally not finalized. Before implementation, compare candidate methods on deterministic daily and intraday examples and specify:

- The measured quantity and units, including how compressed-gap variation maps to horizontal coordinates.
- Whether observations are individual gaps or rolling windows matched to the shift horizon, and how lead length and future-point position affect the range.
- The sample period, minimum sufficient history, treatment of no gaps and outliers, and any quantile or other range rule.
- How estimates behave for backward shifts, uncollapsed mode, streaming updates, reloads, and manual shift adjustments.
- How a user is informed when an estimate cannot be made; lack of evidence must not appear as a zero-uncertainty estimate.

Do not treat empirically estimated bounds as a calibrated confidence interval unless a separate validated statistical model justifies that claim.

### Future labels

Without a future market calendar, historical collapse cannot provide exact future dates. Existing inverse expansion clamps outside the map, so this must not be presented as a correct future date. Define a clearly approximate or explicitly unavailable future axis/cursor representation without changing the meaning of historical dates. Do not construct an exact-looking calendar merely by extrapolating.

## Validation

Use deterministic candle and follower examples at weekly, daily and minute cadences, including weekends, holidays, variable session gaps, future points, both directions, and insufficient history. Cover independent shifts, mode changes, streaming and reprojection, preservation of original timestamps, rendering/legend behavior, uncertainty presentation, and future axis/cursor behavior. Manually inspect the demo with a weekly liquidity-like follower.

## Open Questions / Approval Gate

- Select and specify the historical uncertainty estimator and its visual units after the comparative examples above.
- Specify how approximate-week conversion chooses and refreshes its historical sample, including irregular/missing candles and source replacement.
- Decide the detailed future axis/cursor presentation and how users configure shifts and inspect ranges.
- Confirm performance expectations for many future points and behavior when a shifted econometric series is also selected as the collapse source.

Resolve these questions and review the resulting specification before implementation begins.
