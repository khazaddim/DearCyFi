## Context
X-axis labels on `DearCyFi` plots can overlap after time-collapse transforms or at certain zoom levels. No tooling currently exists to visualize where this happens. This diagnostic overlay is the prerequisite for a future automatic label-thinning algorithm.

The codebase already uses `dcg.PlotDigital` for volume rendering in `DCG_Candle_Utils.py`, text-width measurement via PIL or `char_px` in `locator_time3.py`, and per-resize label recomputation in `core.py:axes_resize_callback`.

## Goals / Non-Goals
- Goals:
  - Provide a visual debug tool that shows the x-extent occupied by each rendered label
  - Make overlap regions immediately visible by eye
  - Reuse existing text-measurement infrastructure — no new dependencies
  - Zero overhead when the overlay is disabled
- Non-Goals:
  - Automatic label removal or thinning (future work informed by this tool)
  - Sub-pixel accuracy or font-kerning-level precision
  - Persisting diagnostic state across sessions

## Decisions

### Use two `dcg.PlotDigital` series for level-0 labels: extents + overlaps
- **What**: Focus diagnostic visualization on level-0 (minor/dense row) labels, which is where overlap actually occurs. Level-1 (major/sparse row) labels are spaced widely enough that overlap is not a practical problem.
  - **Series 1 — "Extents"**: Shows the full x-range occupied by every level-0 label as a high (1.0) digital signal. This is the baseline: you can see how much space each label claims.
  - **Series 2 — "Overlaps"**: Shows only the x-regions where two adjacent level-0 label extents intersect. Because solid PlotDigital bars would mask overlap under the extent bars, a separate series with a distinct color makes overlaps immediately visible.
- **Why**: PlotDigital is already proven in this codebase (volume bars). Its step-function rendering naturally shows rectangular occupied regions. Two series keep the visualization readable: extents give context, overlaps highlight the problem.
- **How overlap intervals are computed**: After building the sorted list of level-0 `(x_start, x_end)` intervals, scan adjacent pairs. If `interval[i].x_end > interval[i+1].x_start`, emit an overlap interval from `interval[i+1].x_start` to `min(interval[i].x_end, interval[i+1].x_end)`.
- **Alternatives considered**:
  - `dcg.DrawRect` inside `DrawInPlot`: More flexible visually, but requires managing individual rect objects per label per resize. PlotDigital handles array updates natively.
  - `dcg.PlotShaded`: Could show overlap as stacked areas, but adds complexity and is harder to read for discrete intervals.
  - Single series with stacked values (1.0 normal, 2.0 overlap): Rejected because PlotDigital renders as flat rectangles — a height difference is subtle and easy to miss compared to a separate colored series.

### Place overlay on a secondary Y-axis with fixed 0–1 range
- **What**: Use a dedicated Y-axis (e.g. `Y2`) locked to [0, 1] with hidden labels/ticks, so the overlay floats in a consistent band and doesn't interfere with price data.
- **Why**: Keeps the price Y-axis clean. The overlay only needs binary high/low, so a 0–1 range is natural.

### Convert pixel widths to axis-coordinate widths using the scaling factor
- **What**: `scaling_factor` from `axes_resize_callback` data gives data-units-per-pixel. Multiply label pixel-width by this factor to get the x-extent in axis coordinates. Center the extent on the label's x-coordinate.
- **Why**: This is the only reliable way to map font-pixel measurements into the same coordinate space as the labels, and the scaling factor is already available in the callback.

### Lazy series creation
- **What**: Don't create the PlotDigital instances in `__init__`. Create them on first enable of `label_overlap_debug`.
- **Why**: Avoids adding plot children (and secondary axis configuration) for users who never use the diagnostic.

### Data flow: from label arrays to PlotDigital series

The diagnostic pipeline runs at the end of `axes_resize_callback`, after the final `labels`, `coords`, and `majors` lists (which include injected boundary ticks) are assembled:

1. **Extent computation** — `_compute_label_extents(labels, coords, is_major_flags, scaling_factor)`:
   - For each label, measure its pixel width using the instance's PIL measurer (or `char_px` fallback).
   - Convert to axis-coordinate half-width: `half_w = (width_px * scaling_factor) / 2.0`.
   - Return `(x_start, x_end, is_major)` where `x_start = coord - half_w`, `x_end = coord + half_w`.
   - Raw pixel widths are not stored — only the `(x_start, x_end)` intervals survive.

2. **Filter to level-0** — keep only entries where `is_major == False` (the dense row where overlaps occur).

3. **Extents series** — flatten the level-0 intervals into PlotDigital step-function arrays:
   ```
   X = [start₀, end₀, start₁, end₁, ...]
   Y = [  1.0,   0.0,   1.0,   0.0, ...]
   ```
   Written to `_diag_extents_series.X` and `.Y`.

4. **Overlap detection** — `_detect_label_overlaps(extents)`:
   - Scan sorted level-0 intervals pairwise.
   - If `extents[i].x_end > extents[i+1].x_start`, emit `(overlap_start, overlap_end, i, i+1)` where `overlap_start = extents[i+1].x_start` and `overlap_end = min(extents[i].x_end, extents[i+1].x_end)`.

5. **Overlaps series** — same step-function pattern but only for the intersection regions:
   ```
   X = [ovl_start₀, ovl_end₀, ovl_start₁, ovl_end₁, ...]
   Y = [       1.0,      0.0,        1.0,      0.0, ...]
   ```
   Written to `_diag_overlaps_series.X` and `.Y`.

6. **Counters** — overlap count and total overlap width (in axis units) are stored in `_last_tick_counts` and surfaced via `_format_debug_text`.

No intermediate width arrays are persisted. The PlotDigital X/Y arrays are the only stored form, and they are rebuilt from scratch on every resize.

## Risks / Trade-offs
- **Risk**: PlotDigital step rendering may not perfectly align with ImPlot's internal label placement (labels are centered, but pixel-to-axis conversion is approximate). → Acceptable for a diagnostic tool; sub-pixel accuracy is a non-goal.
- **Risk**: Frequent series data updates on every resize could add overhead. → The arrays are small (typically <100 labels), so this is negligible compared to the label formatting work already happening.

## Resolved Questions

### Q1: Should the overlay annotate overlap counts or just show visuals?
**Decision**: Two PlotDigital series (extents + overlaps) are sufficient for the diagnostic. The overlap series directly highlights problem regions without needing text annotations. The overlap count will still be tracked in `_last_tick_counts` and surfaced in the debug text overlay, which provides the numeric summary without cluttering the chart.

### Q2: Where should the extent/overlap computation live?
**Context**: The future goal is an automatic label-thinning function that detects overlapping labels and removes excess ones. That function will need the same per-label `(x_start, x_end)` interval computation that the diagnostic overlay uses. We also want to be able to test collision detection against the tick lists that actually exhibit collisions.

**Key insight**: The collisions are caused by `_inject_boundary_ticks_at_discontinuities` in `core.py`, which adds calendar-boundary ticks into the merged tick list *after* the base locator in `locator_time3.py` has run. The final `labels`/`coords`/`majors` arrays — the ones that actually overlap — only exist in `core.py:axes_resize_callback`. The `locator_time3.py` demo has no access to the collapsed time map or boundary injection, so it cannot reproduce the real collision scenarios.

**Decision**: Place the computation as **methods on `DearCyFi` in `core.py`**, not in `locator_time3.py`:

1. `_compute_label_extents(labels, coords, is_major_flags, scaling_factor) -> list[tuple[float, float, bool]]`
   — Takes the final rendered label list (which includes injected boundary ticks) and returns `(x_start, x_end, is_major)` tuples. Uses the same PIL measurer or `char_px` fallback stored on the instance.

2. `_detect_label_overlaps(extents) -> list[tuple[float, float, int, int]]`
   — Takes the sorted extent list, scans adjacent same-lane pairs, and returns `(overlap_start, overlap_end, index_a, index_b)` tuples for every collision.

This placement means:
- Both functions operate on the post-injection label arrays where collisions actually occur.
- The diagnostic overlay in `axes_resize_callback` calls them directly with no import overhead.
- A future thinning algorithm in `core.py` can reuse them in the same callback context.
- If these functions later prove useful as standalone utilities (e.g. for unit testing outside DearCyGui), they can be extracted at that point — but right now the collisions only happen in the `core.py` pipeline.
