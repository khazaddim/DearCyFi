## 1. Core overlay infrastructure

- [ ] 1.1 Add `label_overlap_debug` bool property and backing `_label_overlap_debug` field to `DearCyFi.__init__` (default `False`)
- [ ] 1.2 Add secondary Y-axis (`Y2` or `Y3`) configuration for overlay series, with a fixed 0–1 range and no visible axis chrome
- [ ] 1.3 Create two `dcg.PlotDigital` series instances lazily on first enable, bound to the secondary Y-axis:
  - `_diag_extents_series` — shows the full x-range occupied by each level-0 label
  - `_diag_overlaps_series` — shows only the x-regions where adjacent level-0 extents intersect
- [ ] 1.4 Implement `label_overlap_debug` setter that shows/hides the series and triggers a recompute

## 2. Extent and overlap computation methods in core.py

- [ ] 2.1 Implement `_compute_label_extents(self, labels, coords, is_major_flags, scaling_factor)` as a method on `DearCyFi` returning `list[tuple[float, float, bool]]` (x_start, x_end, is_major) per label — uses the instance's PIL measurer or `char_px` fallback
- [ ] 2.2 Implement `_detect_label_overlaps(extents)` as a static method on `DearCyFi` returning `list[tuple[float, float, int, int]]` (overlap_start, overlap_end, index_a, index_b) for adjacent same-lane collisions

## 3. Diagnostic overlay wiring in core.py axes_resize_callback

- [ ] 3.1 After final `labels`/`coords`/`majors` lists are built, add a guarded block that runs only when `_label_overlap_debug` is `True`
- [ ] 3.2 Call `_compute_label_extents` with the post-injection label arrays, filter to level-0 (non-major) entries, and build the extents PlotDigital X/Y arrays (step-function: high at x_start, low at x_end)
- [ ] 3.3 Call `_detect_label_overlaps` to get overlap intervals and build the overlaps PlotDigital X/Y arrays
- [ ] 3.4 Update both PlotDigital series' X and Y data

## 3. Visual polish and usability

- [ ] 3.1 Choose distinct colors/alpha: semi-transparent fill for extents, a contrasting highlight color for overlaps
- [ ] 3.2 Store overlap count in `_last_tick_counts` (e.g. `overlap_count`, `overlap_total_px`) and include in `_format_debug_text` output
- [ ] 3.3 Add a toggle button or checkbox in `DearCyFi_Demo.py` to enable/disable the overlay at runtime

## 4. Validation

- [ ] 4.1 Manual test: load demo data, enable overlay, zoom/pan, verify extents series tracks level-0 labels
- [ ] 4.2 Manual test: zoom into a region with known overlaps, verify overlaps series highlights intersection regions
- [ ] 4.3 Manual test: collapse time, enable overlay, confirm extent computation uses collapsed coordinates
- [ ] 4.4 Manual test: verify overlay hidden by default and no performance impact when disabled
