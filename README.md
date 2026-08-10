# DearCyFi
DearCyFi is a specialized financial charting widget for use in the DearCyGui GUI library.

## Demo

The primary demo app is maintained in a separate repository:

- https://github.com/khazaddim/DearCyFi_Demo
- Included in this repo as a submodule at `examples/DearCyFi_Demo`

If you cloned this repo without submodules, initialize it with:

```bash
git submodule update --init --recursive
```

## Install

Editable install for development:

```bash
python -m pip install -e .
```

Standard install from source tree:

```bash
python -m pip install .
```

This development branch requires the custom DearCyGui branch that exposes
`dcg.PlotColorBars`. Candle volume and horizontal liquidity overlays fail with
a clear runtime error when that API is unavailable.

## Color Bar Rendering

`PlotCandleStick` renders volume with bottom-anchored `PlotColorBars`. Volume
magnitudes are clipped to non-negative values and normalized so the largest
visible input occupies 20% of the plot height. Up candles use the bull color,
down candles use the bear color, and `volume_kwargs={"colors": ...}` can
override that mapping. The bars use normalized value space and do not affect
axis fitting, so their screen-relative height remains stable during Y-axis
pan and zoom.

`DearCyFi.load_horizontal_bars(...)` uses native right-edge anchoring and
accepts `value_space="data"` or `value_space="normalized"`. Exact apparent
horizontal sizing across every zoom level remains approximate until
volume-weighted price sampling is implemented.

The legacy `dearcyfi.DCG_Bar_Utils.PlotHorizontalBars` helper remains
importable for compatibility but is deprecated. New code should instantiate
`dcg.PlotColorBars(horizontal=True, anchor="axis_max")`.

## Quick Import Check

```python
import dearcygui as dcg

from dearcyfi import DearCyFi, PlotEconometricSeries
```

## Econometric Series

Create low-frequency scalar data directly inside a `DearCyFi` plot:

```python
with chart:
	liquidity = PlotEconometricSeries(
		context,
		dates=weekly_timestamps,
		values=weekly_values,
		label="Weekly Liquidity",
		markers=True,
		y_axis=dcg.Axis.Y3,
	)
```

The series uses native `PlotLine` and optional `PlotScatter` elements. NaN
values break the line by default. Basic observation tooltips show the label,
original source date, and value. `source_dates` remain unchanged when
`set_plot_dates(...)` applies transformed chart coordinates;
`restore_source_dates()` returns the line, markers, and tooltip hit regions to
real time.

Candles and econometric series accept `Y1`, `Y2`, or `Y3` while retaining
`X1` as the shared time axis. Candles default to `Y1` through
`DearCyFi.set_data(..., candle_y_axis=dcg.Axis.Y1)`, and econometric series
default to `y_axis=dcg.Axis.Y1`. The selected axis applies to each complete
composite, including candle volume, econometric markers, and tooltip hit
regions.

The host application owns axis presentation. Enable, label, and fit a secondary
axis explicitly, for example:

```python
chart.Y3.enabled = True
chart.Y3.label = "Weekly Liquidity"
chart.Y3.fit()
```

The optional label-overlap and date-context diagnostics reserve `Y2` as a
hidden fixed scale while enabled. Use `Y1` or `Y3` for application data when
those diagnostics are active.

## Collapse Source Selection

`DearCyFi.set_data(...)` registers its candle series as `"candles"` and selects
it by default. Additional scalar series can follow the same map:

```python
chart.register_time_series(
	"weekly-liquidity",
	liquidity,
	in_gap="next",
)
chart.collapse_source_id = "candles"
chart.collapse_time_chart()
```

Only `collapse_source_id` contributes timestamps to gap detection. A follower
inside a removed interval can use `in_gap="next"` to snap to the first source
timestamp after the gap or `in_gap="previous"` to snap to the last timestamp
before it. Use `restore_time_chart()` to restore all registrations. Removing an
active source also restores the remaining series and clears the selection.
