# Change: Add label overlap diagnostic visualization

## Why
X-axis labels produced by the time locator and boundary-tick injection sometimes overlap, especially after time-collapse transforms or at certain zoom levels. There is currently no visual tool to inspect where overlaps occur, making it hard to design and validate an automatic label-thinning algorithm.

## What Changes
- Add an optional debug overlay to `DearCyFi` that visualizes the pixel-width extent of each rendered label as a `dcg.PlotDigital` series on a secondary Y-axis.
- Separate series for major-lane labels and minor-lane labels, so overlap within each lane and cross-lane collisions are both visible.
- The overlay recomputes on every `axes_resize_callback` using the same label list and text-width measurement infrastructure already in the codebase.
- The overlay is off by default and toggled via a property or method, so it adds zero cost when disabled.

## Impact
- Affected specs: new capability `label-overlap-diagnostic` (no existing specs modified)
- Affected code:
  - `src/dearcyfi/core.py` — new properties/methods and additions to `axes_resize_callback`
  - `src/dearcyfi/core.py:__init__` — optional init parameters and PlotDigital instance storage
  - Potentially `examples/DearCyFi_Demo/DearCyFi_Demo.py` — toggle button for the overlay
