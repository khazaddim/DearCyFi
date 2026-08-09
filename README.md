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
