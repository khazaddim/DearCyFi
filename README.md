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

The series is one legend-enabled `dcg.DrawInPlot` containing drawing
primitives: `DrawPolyline` runs for the line, optional `DrawCircle` markers,
and optional `DrawInvisibleButton` tooltip hit regions. Hiding the series from
the legend hides the line, markers, and tooltips together, and a hidden series
does not affect axis fitting. NaN values or timestamps break the line; they are
never interpolated. Basic observation tooltips show the label, original source
date, and value. `source_dates` remain unchanged when `set_plot_dates(...)`
applies transformed chart coordinates; `restore_source_dates()` returns the
line, markers, and tooltip hit regions to real time.

Styling options (sizes are screen pixels and stay constant while zooming):

| Option | Default |
| --- | --- |
| `line_color` | `(255, 196, 0, 255)` |
| `line_thickness` | `1.5` |
| `marker_color` | same as `line_color` |
| `marker_radius` | `3.0` |

Migration: the former native `line`/`markers` attributes and the
`line_kwargs`/`marker_kwargs` options were removed. Passing either kwargs option
raises a `ValueError`; use the styling options above. Other `DrawInPlot`
options such as `show` or `ignore_fit` are accepted; `axes` is rejected in
favour of `y_axis`.

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

## Candle Indicators

SMA indicators can be calculated directly or managed by a `DearCyFi` chart:

```python
from dearcyfi import SMA

result = SMA(period=20, field="close").calculate({
	"dates": candle_dates,
	"opens": opens,
	"highs": highs,
	"lows": lows,
	"closes": closes,
})
sma_values = result["sma"]

instance = chart.create_indicator(
	type="SMA",
	period=20,
	field="close",
	y_axis=dcg.Axis.Y1,
)
```

The SMA period is a positive integer count of existing candle observations.
The input field is `open`, `high`, `low`, or `close`. Output is `NaN` until
the window is complete and is `NaN` whenever any value in the window is
non-finite. Timestamp gaps do not add synthetic observations or reset the
window. Indicator instances have independent stable IDs and legend entries;
valid edits preserve legend visibility, style, Y-axis, viewport, and time
projection.

Use chart methods to change a managed indicator:

```python
chart.edit_indicator(instance.instance_id, period=30, field="high")
chart.remove_indicator(instance.instance_id)
```

Candle replacement, latest-candle revision, append, and generic
`append_sample("candles", ...)` / `update_last_sample("candles", ...)`
operations recalculate every managed indicator from canonical candle values.
Direct mutation of an indicator is unsupported; mutate candles instead.

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

## Incremental Streaming

Streaming is synchronous and provider-neutral. Bulk-load a series first; each
mutable registration infers its median positive interval from at least two
finite, strictly increasing source timestamps on its first check or mutation.
That cadence remains fixed until `set_data(...)` replaces candle history or
the mutable registration is replaced. Timestamps are Unix seconds as floating
point values; candle timestamps identify interval starts.

The chart exposes generic operations for candle and scalar econometric
registrations:

```python
matches, latest_start = chart.check_last_sample("candles", event.timestamp)
if matches:
    chart.update_last_sample("candles", close=event.close, volume=event.volume)
else:
    chart.append_sample(
        "candles",
        timestamp=event.timestamp,
        open=event.open,
        high=event.high,
        low=event.low,
        close=event.close,
        volume=event.volume,
    )
```

For scalar series, use the same operations with the `"value"` field. Candle
convenience methods are `check_last_candle(timestamp)`,
`append_candle(timestamp=..., open=..., high=..., low=..., close=...,
volume=0.0)`, and `update_last_candle(...)`. The check returns
`(matches_latest_interval, stored_latest_source_timestamp)`; an empty series
returns `(False, None)`. The latest interval is half-open. Its boundary
tolerance in seconds is
`max(min(0.001, interval * 1e-6), 8 * max(ulp(start), ulp(query), ulp(end)))`.
Precision too coarse to distinguish adjacent intervals raises an error.

Append is not an implicit upsert: arrivals less than one cached interval after
the latest source timestamp are rejected. Equal-cadence appends preserve the
real timestamp without removing more time. Longer intervals are accepted as
gaps; while collapsed, only the excess over the cached cadence is removed for
an append to the selected collapse source. While uncollapsed, all accepted
timestamps remain at real coordinates. Latest updates replace only supplied
values. Candle volume is replacement data, and the complete resulting candle
must satisfy finite OHLCV, nonnegative volume, and
`low <= open/close <= high`.
When no candle index was supplied to `set_data`, appended candles extend the
default zero-based index. With a custom index, the appended label is its source
timestamp in seconds rather than a guessed successor for an arbitrary label.

Projection-only registrations remain valid collapse followers but do not
support streaming mutation. A check miss does not guarantee that append will
pass interval and payload validation.

Async providers should normalize events and serialize each check/mutation pair
on the chart-owning thread. There must be no `await` between the check and its
mutation:

```python
def apply_event(chart, event):
    exists, latest_timestamp = chart.check_last_candle(event.timestamp)
    if exists:
        chart.update_last_candle(**event.ohlcv)
    else:
        chart.append_candle(timestamp=event.timestamp, **event.ohlcv)

# Await provider I/O outside this callback, then enqueue apply_event as one
# serialized chart update and report its validation errors to the application.
```

This API does not provide initial bulk collection, broker adapters, historical
correction, calendar-aware cadence policies, tick aggregation, or rendering
optimizations. See the [demo streaming walkthrough](examples/DearCyFi_Demo/README.md)
for a synthetic visual example.

## Interactive Range Boxes

`DearCyFi` now exposes a chart-managed range-box tool whose X anchors stay in
canonical source time even when the visible chart is collapsed:

```python
from dearcyfi import RangeBoxGeometry

chart.set_data(...)

box = chart.add_box(
	geometry=RangeBoxGeometry(
		left_time=source_left_ts,
		bottom=price_low,
		right_time=source_right_ts,
		top=price_high,
	),
	on_geometry_committed=lambda tool, geometry: print(tool.tool_id, geometry),
)
```

Omitting geometry uses a default box derived from the current chart view or
loaded candle extents. `chart.tools` returns all managed interactive tools, and
`chart.boxes` returns just the active range boxes in chart order.

Each `RangeBoxTool` exposes immutable `source_geometry`, projected
`plot_geometry`, semantic `anchor_roles`, and canonical anchor lookup through
`get_anchor(role)`. Programmatic `set_geometry(...)` uses the same validation
and committed-callback path as interactive updates.

Hovering a corner anchor shows a simple tooltip with the tool ID, anchor role,
source-formatted date/time, and current price. These tooltips stay tied to real
timestamps after collapse and update live while an anchor moves.

This initial tool foundation intentionally stops at hover tooltips and range
selection. Fibonacci levels, persistent labels, and candle-derived aggregation
logic remain deferred follow-up work.
