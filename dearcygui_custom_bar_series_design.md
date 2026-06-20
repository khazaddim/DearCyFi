# DearCyGui Custom Bar Series Design

## Purpose

Design a native DearCyGui plot series that:

- renders as a real plot element instead of a `DrawInPlot` child collection
- supports both horizontal and vertical bars
- supports per-bar fill colors
- can optionally anchor bars to the current visible axis minimum or maximum
- shifts with the attached plot axes while panning, with viewport-edge anchors resolved from the live visible limits on every draw
- avoids the visible lag that appears when bar geometry is updated later from a Python resize callback

This is aimed at the use case currently covered by `PlotHorizontalBars` in this repo, where bars are visually tied to a plot edge and can momentarily disconnect while the plot is moving.

## Primary Use Cases

The main target use cases are:

1. Candle volume bars on the time axis with per-bar red and green coloring.
2. Price-resampled volume bars on the price axis with per-bar red and green coloring.
3. Viewport-edge-anchored overlays that remain visually locked to the left, right, top, or bottom side of the active plot while the user pans the main candle plot.

In practice that means:

- vertical bars should support a candle-volume style presentation on the X axis
- horizontal bars should support price-binned or price-resampled volume on the Y axis
- both styles should support bull/bear coloring per bar without splitting the data into many separate series

## Problem Summary

The current local implementation in `src/dearcyfi/DCG_Bar_Utils.py` creates one `DrawRect` per bar and updates `pmin` and `pmax` from Python after axis changes. That means the bars are not evaluated from the active plot transform during the same draw pass as the plot itself.

This has two consequences:

1. Bars can appear one callback behind the plot while panning or zooming.
2. Per-bar styling is expensive because it is expressed as many child draw items rather than one native plot element.

The right fix is a native DearCyGui series whose geometry is computed inside `draw_element()` against the current plot state.

## Relevant DearCyGui Architecture

The installed DearCyGui stubs and declarations show a clean path for this.

### Plot ownership

- `Plot` is a `uiItem` that owns axis config and legend config.
- Plot children are plot elements attached to one X axis and one Y axis.

### Native series shape

- `plotElement` is the base class for plot children.
- `plotElementWithLegend` adds legend participation, theme support, enable/show state, and a `draw_element()` override point.
- `plotElementXY` adds `_X` and `_Y` array storage plus array validation.

That is the same inheritance family used by `PlotLine`, `PlotBars`, `PlotScatter`, and `PlotDigital`.

### Existing bar precedent

`PlotBars` already proves that DearCyGui supports a native bar-series API with:

- `horizontal: bool`
- `weight: float`
- `X` and `Y` arrays

What it does not provide is per-bar color control or viewport-edge anchoring.

### Existing wrapper helpers

The installed wrappers already expose the primitives needed for a custom renderer:

- `implot.PlotToPixels(...)`
- `implot.GetPlotLimits(...)`
- `implot.GetPlotDrawList()`
- `implot.PushPlotClipRect()` / `implot.PopPlotClipRect()`
- `ImDrawList.AddRectFilled(...)`
- `ImDrawList.AddRect(...)`

That means a custom series can be implemented without first extending the wrapper layer.

## Recommendation

Add a new native plot series instead of modifying `PlotBars`.

Recommended public name:

- `PlotColorBars`

Why a new class is cleaner than extending `PlotBars`:

1. `PlotBars` likely maps closely to the plain ImPlot bar calls, while per-bar colors require a custom draw loop.
2. Edge anchoring changes the mental model from "bars from a fixed baseline" to "bars from a live viewport edge."
3. A dedicated class avoids hidden mode switches inside `PlotBars` and keeps the existing API stable.

## Proposed Public API

```python
class PlotColorBars(plotElementXY):
    def __init__(
        self,
        context,
        *,
        X=...,
        Y=...,
        colors=...,
        line_colors=...,
        horizontal=False,
        weight=1.0,
        anchor="baseline",
        anchor_value=0.0,
        ignore_fit=False,
        label="",
        axes=(Axis.X1, Axis.Y1),
        theme=...,
        show=True,
        enabled=True,
        no_legend=False,
        user_data=...,
    ):
        ...
```

### Parameters

- `X`, `Y`
  - Vertical mode: `X` is bar center positions, `Y` is bar lengths.
  - Horizontal mode: `Y` is bar center positions, `X` is bar lengths.
- `colors`
  - Optional per-bar fill colors.
  - Uses DearCyGui packed color integers or any accepted Python color input converted during assignment.
- `line_colors`
  - Optional per-bar border colors.
  - If omitted, borders are disabled by default.
- `horizontal`
  - `False` for vertical bars.
  - `True` for horizontal bars.
- `weight`
  - Thickness of each bar in plot units on the orthogonal axis.
- `anchor`
  - One of: `"baseline"`, `"axis_min"`, `"axis_max"`.
- `anchor_value`
  - Used only when `anchor == "baseline"`.
  - Default `0.0`.
- `ignore_fit`
  - For edge-anchored bars, the recommended default is `True`.

### Color behavior

- If `colors` is omitted, the series fill falls back to the series theme.
- If `colors` is length 1, it may be broadcast to all bars.
- If `colors` is the same length as the bar count, each bar uses its own fill color.
- Any other length is a validation error.

### Anchor behavior

- `baseline`
  - Standard bars from a fixed plot value.
- `axis_min`
  - Bars grow inward from the currently visible minimum of the primary value axis.
- `axis_max`
  - Bars grow inward from the currently visible maximum of the primary value axis.

For horizontal bars, the primary value axis is X.

For vertical bars, the primary value axis is Y.

## Pan and Axis-Locking Semantics

This design is intended to follow the main candle plot while panning.

If the custom series is attached to the same plot axes as the candle plot:

- panning the candle plot causes the custom bar series to move with it
- zooming the candle plot causes the custom bar series to rescale with it on its attached axes
- when `anchor="axis_min"` or `anchor="axis_max"` is used, the anchored side is recomputed from the current visible axis limits during `draw_element()`

That means the series behaves like your current horizontal bars in intent, but without the one-callback-behind lag, because the edge anchor is resolved during the same render pass as the plot.

### Important distinction from `PlotDigital`

The current design is viewport-edge anchored, but it is still a normal plot series in data coordinates.

The bars are not meant to sit offscreen and then have their max or min values patched later to fake the lock.

Instead, the series is redrawn natively each frame from the current visible axis limits. In other words:

- DearCyGui asks the series to render
- the series reads the live visible plot limits for its attached axes
- the anchored side of each bar is set directly to the current visible edge
- the rectangle is drawn immediately from that edge inward

So the effect comes from fresh geometry computed during native plot rendering, not from a delayed Python callback and not from shifting previously drawn bars after the fact.

So there are two related but different behaviors:

1. `axis_min` / `axis_max` anchoring
  - the bar starts from the current visible axis edge
  - the bar is redrawn from that edge every render pass
  - the bar moves correctly as the plot pans
  - the bar length is still interpreted in plot-axis units

2. `PlotDigital`-style fixed-band behavior
  - the signal is visually anchored to the plot edge
  - the signal does not scale with the plot's value-axis zoom in the same way as ordinary data series

For horizontal price-resampled volume bars on the Y axis, the current `axis_max` or `axis_min` design is the right fit.

For candle volume at the bottom of the chart, the current design is sufficient if you want normal plot-axis behavior or if you render on a dedicated fixed secondary axis.

If you want exact `PlotDigital`-style bottom-band behavior for vertical volume bars, the design should also support one of these approaches:

- attach the volume series to a dedicated secondary axis with a fixed range such as `Y2 = [0, 1]`
- add a future property such as `value_space="data" | "normalized"`

The first option is simpler and is probably enough for the candle-volume use case.

### Concrete mental model

For a right-anchored horizontal bar, the renderer should behave like this on every draw:

```text
visible_right = current visible X-axis max
bar_right = visible_right
bar_left = visible_right - bar_width
```

For a bottom-anchored vertical bar on a fixed secondary axis, the renderer should behave like this on every draw:

```text
visible_bottom = current visible Y-axis min of the attached axis
bar_bottom = visible_bottom
bar_top = visible_bottom + bar_height
```

That is the locking behavior. The bars go directly to the current visible edge because their geometry is rebuilt from the current viewport limits during each native render.

## Why This Solves the Lag

The current lag exists because Python mutates many `DrawRect` children after the plot range already changed.

In a native series, `draw_element()` runs during plot rendering and reads the live plot limits in the same frame. The bar endpoints are therefore computed from the same transform the rest of the plot is using.

That removes the callback timing gap.

## Internal Cython Shape

At the Cython level, this should look like a normal plot series, not a `DrawInPlot` helper.

Suggested declaration:

```cython
cdef class PlotColorBars(plotElementXY):
    cdef DCG1DArrayView _colors
    cdef DCG1DArrayView _line_colors
    cdef double _weight
    cdef bint _horizontal
    cdef int32_t _anchor_mode
    cdef double _anchor_value
    cdef bint _ignore_fit
    cdef void check_arrays(self) noexcept nogil
    cdef void draw_element(self) noexcept nogil
```
```

Notes:

- If `DCG1DArrayView` does not cleanly support packed `uint32` colors, add a dedicated packed-color array view type instead of forcing conversions on every draw.
- Reuse DearCyGui's existing packed-color format so bar colors match theme and draw-list expectations.

## Rendering Strategy

Implement `draw_element()` as a custom draw-list renderer instead of calling `ImPlot::PlotBars`.

### Why not wrap `ImPlot::PlotBars`?

Because the current wrapper surface only exposes whole-series styling for bars. Per-bar colors require a bar-by-bar draw loop.

### Draw loop outline

```cython
cdef void draw_element(self) noexcept nogil:
    cdef int i, count
    cdef double center, length, start_value, end_value
    cdef double half_weight
    cdef ImPlotRect limits
    cdef ImVec2 pmin, pmax
    cdef ImDrawList* draw_list
    cdef ImU32 fill_col, line_col

    self.check_arrays()
    count = len(self._X)
    if count == 0:
        return

    limits = implot.GetPlotLimits(self._axes[0], self._axes[1])
    draw_list = implot.GetPlotDrawList()
    half_weight = self._weight * 0.5

    implot.PushPlotClipRect()
    try:
        for i in range(count):
            if self._horizontal:
                center = self._Y[i]
                length = self._X[i]
                start_value = resolve_anchor_x(limits, self._anchor_mode, self._anchor_value)
                end_value = start_value + signed_length_from_anchor(length, self._anchor_mode)

                pmin = implot.PlotToPixels(min(start_value, end_value), center - half_weight, self._axes[0], self._axes[1])
                pmax = implot.PlotToPixels(max(start_value, end_value), center + half_weight, self._axes[0], self._axes[1])
            else:
                center = self._X[i]
                length = self._Y[i]
                start_value = resolve_anchor_y(limits, self._anchor_mode, self._anchor_value)
                end_value = start_value + signed_length_from_anchor(length, self._anchor_mode)

                pmin = implot.PlotToPixels(center - half_weight, min(start_value, end_value), self._axes[0], self._axes[1])
                pmax = implot.PlotToPixels(center + half_weight, max(start_value, end_value), self._axes[0], self._axes[1])

            fill_col = resolve_fill_color(i)
            draw_list.AddRectFilled(pmin, pmax, fill_col, 0.0, 0)

            if borders_enabled:
                line_col = resolve_line_color(i)
                draw_list.AddRect(pmin, pmax, line_col, 0.0, 0, 1.0)
    finally:
        implot.PopPlotClipRect()
```

### Key point

The anchor is resolved from `GetPlotLimits(...)` inside `draw_element()`, not from a Python resize callback.

## Axis and Fit Semantics

### Standard baseline bars

- `anchor="baseline"`
- participate in normal fit behavior
- act like a more flexible `PlotBars`

### Edge-anchored bars

- `anchor="axis_max"` is the direct replacement for the current right-anchored horizontal bars
- `anchor="axis_min"` supports left-anchored horizontal bars or bottom-anchored vertical bars
- these should usually be created with `ignore_fit=True`

When attached to the same axes as the main chart, these bars should visibly shift with pan operations because the anchor is resolved from the current visible limits every frame.

Reason:

Edge-anchored bars are a viewport decoration pattern. They should usually not push auto-fit outward just because the user loaded them.

## Validation Rules

Validation should happen once during assignment or `configure()`, not every frame beyond a cheap final assertion.

Required checks:

1. `len(X) == len(Y)`
2. `len(colors)` is `0`, `1`, or `len(X)`
3. `len(line_colors)` is `0`, `1`, or `len(X)`
4. `weight > 0`
5. `anchor` is one of the supported values

## Example Python Usage

### Example 1: Vertical bars with per-bar colors

```python
import numpy as np
import dearcygui as dcg

C = dcg.Context()

with dcg.Plot(C, label="Per-Bar Vertical", width=800, height=300):
    x = np.arange(6, dtype=float)
    y = np.array([4.0, 2.0, 5.5, 1.5, 3.0, 4.5], dtype=float)
    colors = [
        (230, 70, 70, 180),
        (70, 160, 240, 180),
        (250, 190, 50, 180),
        (120, 210, 120, 180),
        (200, 90, 220, 180),
        (80, 210, 200, 180),
    ]

    dcg.PlotColorBars(
        C,
        X=x,
        Y=y,
        colors=colors,
        weight=0.8,
        anchor="baseline",
        anchor_value=0.0,
        label="Volume by bucket",
    )
```

  This is the basic red/green candle-volume style shape, assuming `colors` is chosen from bull/bear state.

  ### Example 1b: Bottom-band candle volume on a fixed secondary axis

  ```python
  import numpy as np
  import dearcygui as dcg

  C = dcg.Context()

  with dcg.Plot(C, label="Candles With Volume", width=1000, height=500) as plot:
    plot.Y2.enabled = True
    plot.Y2.constraint_min = 0.0
    plot.Y2.constraint_max = 1.0
    plot.Y2.lock_min = True
    plot.Y2.lock_max = True
    plot.Y2.no_tick_labels = True
    plot.Y2.no_tick_marks = True
    plot.Y2.no_gridlines = True

    x = np.arange(100, dtype=float)
    volume = np.random.uniform(0.05, 0.45, size=100)
    closes_up = np.random.randint(0, 2, size=100).astype(bool)
    colors = [
      (70, 190, 110, 170) if is_up else (210, 80, 80, 170)
      for is_up in closes_up
    ]

    dcg.PlotColorBars(
      C,
      X=x,
      Y=volume,
      colors=colors,
      weight=0.8,
      anchor="axis_min",
      axes=(dcg.Axis.X1, dcg.Axis.Y2),
      ignore_fit=True,
      label="Candle Volume",
    )
  ```

  This is the closer analog to `PlotDigital` behavior for candle volume, because the bar series pans with X while living on a dedicated fixed vertical band.

### Example 2: Right-anchored horizontal bars

```python
import numpy as np
import dearcygui as dcg

C = dcg.Context()

with dcg.Plot(C, label="Right-Anchored Bars", width=900, height=500) as plot:
    y_positions = np.array([101.0, 104.0, 107.0, 111.0], dtype=float)
    widths = np.array([2.0, 5.0, 3.5, 6.5], dtype=float)
    fills = [
        (220, 90, 90, 140),
        (90, 190, 240, 140),
        (240, 180, 70, 140),
        (120, 220, 140, 140),
    ]

    dcg.PlotColorBars(
        C,
        X=widths,
        Y=y_positions,
        colors=fills,
        horizontal=True,
        weight=1.5,
        anchor="axis_max",
        ignore_fit=True,
        label="Liquidity lanes",
    )
```

This is the use case that should eliminate the current visual disconnect during pan and zoom.

It is also the direct template for red/green price-resampled volume on the price axis: `Y` stays in price coordinates, the series pans with the chart, and the visible right edge anchor is recomputed every draw.

### Example 3: Interleaved horizontal lanes with two color families

```python
import numpy as np
import dearcygui as dcg

C = dcg.Context()

with dcg.Plot(C, label="Interleaved Lanes", width=900, height=500):
    lane_a_y = np.array([100.0, 102.0, 104.0, 106.0], dtype=float)
    lane_b_y = lane_a_y + 0.7

    dcg.PlotColorBars(
        C,
        X=np.array([4.0, 3.0, 5.0, 2.5], dtype=float),
        Y=lane_a_y,
        colors=[(60, 170, 240, 150)] * 4,
        horizontal=True,
        weight=0.5,
        anchor="axis_max",
        ignore_fit=True,
        label="Lane A",
    )

    dcg.PlotColorBars(
        C,
        X=np.array([2.0, 4.5, 3.5, 6.0], dtype=float),
        Y=lane_b_y,
        colors=[(240, 120, 80, 150)] * 4,
        horizontal=True,
        weight=0.5,
        anchor="axis_max",
        ignore_fit=True,
        label="Lane B",
    )
```

## Suggested DearCyGui Source Touch Points

Assuming the actual DearCyGui source tree matches the installed declarations, the likely changes are:

1. `dearcygui/plot.pxd`
   - add the `PlotColorBars` cdef declaration

2. DearCyGui plot implementation `.pyx`
   - add storage, validation, property setters, and `draw_element()`

3. `dearcygui/core.pyi`
   - add the public Python signature and property docs

4. Demo/docs
   - add one vertical example and one edge-anchored horizontal example

## Suggested Property Additions

```python
series.colors
series.line_colors
series.horizontal
series.weight
series.anchor
series.anchor_value
```

## Trade-offs

### Benefits

- removes Python callback lag for edge-anchored bars
- supports per-bar color without one child draw item per bar
- keeps legend and axis attachment behavior consistent with native plot series
- keeps the current `PlotHorizontalBars` use case in one series rather than a draw-item collection
- supports the two target market-chart overlays: red/green candle volume and red/green price-resampled volume

### Costs

- more custom rendering code than simply wrapping one ImPlot function
- per-bar colors mean the renderer cannot rely on a single whole-series fill style
- hover or hit-testing would need a separate design if later required

## Migration Path From This Repo

The current local class:

- `PlotHorizontalBars` in `src/dearcyfi/DCG_Bar_Utils.py`

could be replaced with:

```python
dcg.PlotColorBars(
    context,
    X=bar_lengths,
    Y=y_positions,
    colors=bar_colors,
    horizontal=True,
    weight=bar_height,
    anchor="axis_max",
    ignore_fit=True,
)
```

That removes the need for:

- maintaining `DrawRect` children
- Python-side `update_positions()` logic
- axis resize callback geometry rewrites just to keep bars attached to the edge

## Bottom Line

If the goal is a smooth, edge-anchored bar series with per-bar color control, implement it as a new native DearCyGui plot element with a custom `draw_element()` loop.

Do not build the final solution on top of `DrawInPlot` plus Python callbacks.

The wrapper surface already exposes the plot-to-pixel and draw-list hooks needed to do this cleanly.