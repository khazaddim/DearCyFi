# Change: Fix collapsed X-axis timestamps outside the source range

## Why

Collapsed X-axis ticks before and after the selected collapse source all display the first or last source timestamp. This also mislabels the coordinates of registered followers, such as a weekly econometric series extending beyond the loaded candles, even though their forward projection preserves their time offsets.

## What Changes

- Use the inverse of the existing follower projection for X-axis labels outside the selected source range. Apply the same conversion to regular ticks and supplemental date-context labels.
- Keep known follower observations tied to their original timestamps. Format all tick and cursor dates normally, without a per-label marker or inference from a trading calendar.
- Use the same timestamp conversion for the cursor tag so it does not display a contradictory source endpoint. Preserve in-range and bridge labeling, original-time mode, observation tooltips, and drawing-tool conversions.
- Document the mapping formulas, the limits of the mapping, and a reproducible demo check.

## Impact

- Affected specs: `time-collapse-coordination`, `collapsed-time-cursor-tag`.
- Expected code areas: [`GapCollapsedTimeMap`](../../../src/dearcyfi/candle_utils/gap_utils.py), [DearCyFi custom X-axis labels](../../../src/dearcyfi/core.py), gap and axis tests, and [README](../../../README.md).
- No changes to forward projection, series data, or dependencies. The pending econometric display-shift proposal remains responsible for deliberately shifted observations.
