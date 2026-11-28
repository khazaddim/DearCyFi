# Change: Fix collapsed X-axis timestamps outside the source range

## Why

Collapsed X-axis ticks before and after the selected collapse source all display the first or last source timestamp. This also mislabels the coordinates of registered followers, such as a weekly econometric series extending beyond the loaded candles, even though their forward projection preserves their time offsets.

## What Changes

- Use the inverse of the existing follower projection for X-axis labels outside the selected source range. Apply the same conversion to regular ticks and supplemental date-context labels.
- Keep known follower observations tied to their original timestamps. Mark exterior labels without a matching observation as extrapolated, not as dates inferred from a trading calendar.
- Preserve in-range and bridge labeling, original-time mode, observation tooltips, and existing cursor and drawing-tool conversions.
- Document the mapping formulas, the distinction between observed and extrapolated dates, and a reproducible demo check.

## Impact

- Affected spec: `time-collapse-coordination`.
- Expected code areas: [`GapCollapsedTimeMap`](../../../src/dearcyfi/candle_utils/gap_utils.py), [DearCyFi custom X-axis labels](../../../src/dearcyfi/core.py), gap and axis tests, and [README](../../../README.md).
- No changes to forward projection, series data, public APIs, or dependencies. The pending econometric display-shift proposal remains responsible for shifted observations and future cursor presentation.
