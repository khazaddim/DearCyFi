## ADDED Requirements

### Requirement: Label Extent Diagnostic Overlay
The `DearCyFi` plot SHALL provide an optional diagnostic overlay that renders the pixel-width extent of level-0 (minor/dense row) X-axis labels as digital plot series, so developers can visually identify label overlaps. Level-1 (major/sparse row) labels are excluded because they do not exhibit overlap in practice.

#### Scenario: Overlay disabled by default
- **WHEN** a `DearCyFi` plot is created with default parameters
- **THEN** no diagnostic overlay series are visible on the plot
- **AND** the axes resize callback does not perform overlay computation

#### Scenario: Overlay enabled at runtime
- **WHEN** the developer sets the `label_overlap_debug` property to `True`
- **THEN** two `dcg.PlotDigital` series appear on a secondary Y-axis:
  - An **extents** series showing the full occupied x-range of each level-0 label
  - An **overlaps** series showing only the x-regions where adjacent level-0 label extents intersect

#### Scenario: Overlay updates on axes resize
- **WHEN** the overlay is enabled and the user pans or zooms the X-axis
- **THEN** the overlay series are recomputed from the current label list, coordinates, and text-width measurements
- **AND** the updated series reflect the new visible range

#### Scenario: Width measurement consistency
- **WHEN** the overlay computes label extents
- **THEN** it SHALL use the same text-width measurement function (PIL measurer or `char_px` fallback) that the `TimeAxisLocator` uses
- **AND** convert pixel widths to axis-coordinate widths using the current scaling factor from the resize callback

#### Scenario: Overlap regions visually distinct
- **WHEN** two adjacent level-0 labels have overlapping x-extents
- **THEN** the overlaps series highlights the intersection region in a distinct color from the extents series
- **AND** the overlap is immediately visible even when rendered on top of the extents series

### Requirement: Label Extent and Overlap Computation Methods
The `DearCyFi` class SHALL provide methods for computing label extents and detecting overlaps on the final merged label arrays (including injected boundary ticks), so both the diagnostic overlay and future label-thinning logic can share the same computation.

#### Scenario: Extent intervals match rendered labels
- **WHEN** `_compute_label_extents` is called with the final rendered labels, coordinates, major flags, and scaling factor
- **THEN** it returns one `(x_start, x_end, is_major)` tuple per label
- **AND** the x-extent for each label equals its measured pixel width converted to axis coordinates, centered on the label's coordinate

#### Scenario: Overlap detection finds collisions from injected boundary ticks
- **WHEN** `_detect_label_overlaps` is called with the sorted extent list that includes boundary-injected labels
- **THEN** it returns `(overlap_start, overlap_end, index_a, index_b)` tuples for every pair of adjacent same-lane labels whose extents intersect

### Requirement: Overlay Toggle Interface
The `DearCyFi` plot SHALL expose a simple interface to enable and disable the diagnostic overlay without requiring plot recreation.

#### Scenario: Toggle on
- **WHEN** `label_overlap_debug` is set to `True` on an existing plot
- **THEN** the overlay series are created (if not already present) and become visible

#### Scenario: Toggle off
- **WHEN** `label_overlap_debug` is set to `False`
- **THEN** the overlay series are hidden or removed
- **AND** the axes resize callback skips overlay computation
