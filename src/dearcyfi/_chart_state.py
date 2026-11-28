"""Adapters between portable chart records and chart-owned runtime items."""

import logging
import math
from dataclasses import asdict

import dearcygui as dcg
import numpy as np

from ._chart_document import (
    AXES, BOX_COLORS, FORMAT, ITEM_FLAGS, LEGEND_FLAGS, VERSION, BarRecord,
    ChartDocument, ChartPersistenceError, DrawingRecord, IndicatorRecord, SourceRecord,
    validate_document,
)
from .candle_indicators import SMA, PlotCandleIndicatorSeries
from .candle_utils.gap_utils import GapCollapsedTimeMap
from .core import DearCyFi, _CandleSeriesAdapter
from .DCG_Candle_Utils import PlotCandleStick
from .econometric_series import PlotEconometricSeries
from .range_box_tools import RangeBoxGeometry, RangeBoxTool

log = logging.getLogger(__name__)
_DIAGNOSTICS = ("_diag_extents_series", "_diag_overlaps_series", "_diag_date_context_series")
_DIAGNOSTIC_AXIS = ("constraint_min", "constraint_max", "lock_min", "lock_max",
                    "no_tick_labels", "no_tick_marks", "no_gridlines", "no_label",
                    "no_side_switch", "no_highlight", "no_menus")

_CONTENTS = (
    "dates", "opens", "highs", "lows", "closes", "index", "volume", "_index_is_default",
    "candlestick_plot", "horizontal_bars", "_time_series", "_plot_dates_by_id",
    "_time_series_sorted", "_stream_cadences", "_collapse_source_id", "_gap_manager",
    "_indicator_manager", "_tools", "_tool_ids", "_next_tool_number",
    "_time_locator", "_time_locator_use_local_time", "_time_locator_use_24_hour",
    "_time_locator_use_iso8601", "_vectorized_collapse", "_apply_date_context_labels",
    "_last_axis_resize_info", "_last_resize_time_format_info", "_last_tick_counts",
    "_anchor_tooltips_enabled", "_label_overlap_debug", "_date_context_debug", *_DIAGNOSTICS,
)
_AXIS_PRESENTATION = ("enabled", "label", "scale", "invert", "opposite")
_AXIS_ROLLBACK = (*_AXIS_PRESENTATION, "min", "max", "no_initial_fit", "auto_fit")
_TICKS = ("keep_default_ticks", "labels", "labels_coord", "labels_major", "no_gridlines")
_NATIVE_TIME = ("use_local_time", "use_24hour_clock", "use_ISO8601")
_LEGEND = ("location", *LEGEND_FLAGS)


def _properties(obj, names):
    return {name: getattr(obj, name) for name in names}


def _configure(obj, properties):
    for name, value in properties.items():
        setattr(obj, name, value)


def _colors(values):
    if values is None:
        return []
    try:
        return [list(dcg.color_as_ints(values))]
    except (TypeError, ValueError):
        return [list(dcg.color_as_ints(value)) for value in values]


def _scalar(value):
    if isinstance(value, (np.integer, np.floating, np.bool_, np.str_)):
        return value.item()
    return value


def _column(values, *, missing=False):
    column = np.asarray(values).tolist()
    if missing and isinstance(column, list):
        return [None if type(value) is float and math.isnan(value) else value for value in column]
    return column


def _item_display(item, *, axis=True):
    display = _properties(item, ("label", *ITEM_FLAGS))
    if axis:
        if item.axes[0] != dcg.Axis.X1:
            raise ChartPersistenceError(f"{item.label!r}: only X1 items can be saved")
        display["y_axis"] = item.axes[1].name
    return display


def _item_kwargs(display):
    result = dict(display)
    if "y_axis" in result:
        result["y_axis"] = dcg.Axis[result["y_axis"]]
    return result


def _line_display(item):
    return {
        **_item_display(item),
        "line_color": list(dcg.color_as_ints(item._line_color)),
        "line_thickness": item._line_thickness,
        "markers": item._markers,
        "marker_color": list(dcg.color_as_ints(item._marker_color)),
        "marker_radius": item._marker_radius,
        "tooltip": bool(item._tooltip),
    }


def _bar_display(item, *, volume=False):
    return {
        **_item_display(item, axis=not volume),
        **_properties(item, ("anchor", "anchor_value", "value_space", "normalized_max_fraction", "weight")),
        "colors": [list(dcg.color_as_ints(color)) for color in item.colors],
        "line_colors": [list(dcg.color_as_ints(color)) for color in item.line_colors],
    }


def _capture_candles(chart, item_id, registration) -> SourceRecord:
    candle = registration.series.candle
    if candle is not chart.candlestick_plot or type(candle) is not PlotCandleStick:
        raise ChartPersistenceError(f"series {item_id!r}: unsupported candle ownership or type")
    volume = candle._volume_bar_series
    if volume.horizontal or volume.axes != candle.axes:
        raise ChartPersistenceError(f"series {item_id!r}: unsupported volume orientation or axes")
    volume_display = _bar_display(volume, volume=True)
    volume_display["colors"] = (
        None if candle._volume_color_override is None else _colors(candle._volume_color_override)
    )
    volume_display["auto_weight"] = candle._volume_uses_default_weight
    return {
        "id": item_id, "kind": "candles", "in_gap": registration.in_gap,
        "data": {
            "dates": _column(candle.source_dates),
            "open": _column(candle.opens), "high": _column(candle.highs),
            "low": _column(candle.lows), "close": _column(candle.closes),
            "volume": _column(candle.volumes, missing=True) if len(candle.volumes) else None,
            "index": None if chart._index_is_default else [
                _scalar(value) for value in chart.index
            ],
            "time_counts": (
                [[_scalar(value) for value in row] if row is not None else [] for row in candle.time_counts]
                if candle.time_counts is not None and len(candle.time_counts) else None
            ),
        },
        "display": {
            **_item_display(candle),
            "bull_color": list(dcg.color_as_ints(candle._bull_color)),
            "bear_color": list(dcg.color_as_ints(candle._bear_color)),
            "weight": candle._weight, "tooltip": bool(candle._tooltip),
            "count_position": candle._count_position, "count_offset": candle._count_offset,
            "volume": volume_display,
        },
    }


def _capture_econometric(_chart, item_id, registration) -> SourceRecord:
    item = registration.series
    return {
        "id": item_id, "kind": "econometric", "in_gap": registration.in_gap,
        "data": {"dates": _column(item.source_dates), "values": _column(item.values, missing=True)},
        "display": _line_display(item),
    }


def _capture_bars(chart) -> BarRecord:
    item = chart.horizontal_bars
    if type(item) is not dcg.PlotColorBars or not item.horizontal:
        raise ChartPersistenceError("series 'horizontal-bars': expected horizontal PlotColorBars")
    return {
        "id": chart._horizontal_bars_id, "kind": "horizontal-bars",
        "data": {"lengths": _column(item.X), "levels": _column(item.Y)},
        "display": _bar_display(item),
    }


def _capture_sma(instance) -> IndicatorRecord:
    return {
        "id": instance.instance_id, "kind": "sma", "input": "candles",
        "parameters": dict(instance.calculator.parameters),
        "display": _line_display(instance.series),
    }


def _capture_range_box(tool) -> DrawingRecord:
    return {
        "id": tool.tool_id, "kind": "range-box", "geometry": asdict(tool.source_geometry),
        "options": {
            "anchor_tooltips_enabled": tool.anchor_tooltips_enabled,
            "hit_size": tool._hit_size,
            "min_source_width": tool._min_source_width,
            "min_source_height": tool._min_source_height,
        },
        "display": {
            "y_axis": tool.y_axis.name,
            **{name: list(dcg.color_as_ints(getattr(tool, f"_{name}"))) for name in BOX_COLORS},
        },
    }


_SOURCE_CAPTURE = {_CandleSeriesAdapter: _capture_candles, PlotEconometricSeries: _capture_econometric}
_INDICATOR_CAPTURE = {SMA: _capture_sma}
_DRAWING_CAPTURE = {RangeBoxTool: _capture_range_box}


def _range(axis):
    limits = (axis.min, axis.max)
    if not (axis.state.visible or axis.no_initial_fit or limits != (0.0, 1.0)):
        return None
    if all(math.isfinite(value) for value in limits) and limits[0] < limits[1]:
        return list(limits)
    return None


def capture_chart(chart: DearCyFi, *, validate: bool = True) -> ChartDocument:
    with chart.mutex:
        instances = chart.indicator_instances
        registrations = {instance.registration_id: instance.series for instance in instances.values()}
        series = {}
        for item_id, registration in chart._time_series.items():
            item = chart.get_time_series(item_id)
            if item_id in registrations and registrations[item_id] is item:
                continue
            handler = _SOURCE_CAPTURE.get(type(registration.series))
            if handler is None:
                raise ChartPersistenceError(f"series {item_id!r}: unsupported {type(item).__name__}")
            if (item.parent is not None and item.parent is not chart) or item in series:
                raise ChartPersistenceError(f"series {item_id!r}: expected a unique series owned by this chart")
            if isinstance(registration.series, _CandleSeriesAdapter) and item.parent is not chart:
                raise ChartPersistenceError(f"series {item_id!r}: candles are not attached to this chart")
            series[item] = handler(chart, item_id, registration)
        if chart.candlestick_plot is not None and chart.candlestick_plot not in series:
            raise ChartPersistenceError("series 'candles': the owned candle plot is not registered")
        if chart.horizontal_bars is not None:
            if chart.horizontal_bars.parent is not chart:
                raise ChartPersistenceError("series 'horizontal-bars': bars are not attached to this chart")
            series[chart.horizontal_bars] = _capture_bars(chart)
        indicators = []
        for instance in instances.values():
            handler = _INDICATOR_CAPTURE.get(type(instance.calculator))
            if handler is None or type(instance.series) is not PlotCandleIndicatorSeries:
                raise ChartPersistenceError(
                    f"indicator {instance.instance_id!r}: unsupported {type(instance.calculator).__name__}"
                )
            registration = chart._time_series.get(instance.registration_id)
            if (registration is None or registration.series is not instance.series
                    or instance.series.parent is not chart or registration.in_gap != "next"):
                raise ChartPersistenceError(f"indicator {instance.instance_id!r}: inconsistent registration")
            indicators.append(handler(instance))
        drawings = []
        for tool in chart.tools:
            handler = _DRAWING_CAPTURE.get(type(tool))
            if handler is None or tool.disposed:
                raise ChartPersistenceError(f"drawing {tool.tool_id!r}: unsupported or disposed {tool.tool_kind}")
            drawings.append(handler(tool))
        gap_map = chart._gap_manager.time_map if chart.time_is_collapsed else None
        axes = {}
        for name in AXES:
            axis = getattr(chart, name)
            axes[name] = {**_properties(axis, _AXIS_PRESENTATION), "scale": axis.scale.name,
                          "range": _range(axis)}
        axes["X1"]["space"] = "source" if gap_map is None else "collapsed"
        children = chart.children
        attached = set(children)
        document: ChartDocument = {
            "format": FORMAT, "version": VERSION,
            "chart": {
                "axes": axes,
                "legend": {
                    **_properties(chart.legend_config, _LEGEND), "show": not chart.no_legend,
                    "location": chart.legend_config.location.name,
                },
                "anchor_tooltips_enabled": chart.anchor_tooltips_enabled,
                "time": {
                    "source": chart.collapse_source_id,
                    "vectorized": chart.vectorized_collapse,
                    "gaps": None if gap_map is None else gap_map.gap_definitions(),
                    "active_method": chart._gap_manager.active_method,
                    "stream_interval": chart._stream_cadences.get(chart.collapse_source_id),
                    "use_local_time": bool(chart._time_locator_use_local_time),
                    "use_24_hour": bool(chart._time_locator_use_24_hour),
                    "use_iso8601": bool(chart._time_locator_use_iso8601),
                    "date_context_labels": chart.apply_date_context_labels,
                },
            },
            "series": ([series[child] for child in children if child in series]
                       + [record for item, record in series.items() if item not in attached]),
            "indicators": indicators,
            "drawings": drawings,
        }
    return validate_document(document) if validate else document


def _restore_candles(stage, record):
    data = record["data"]
    display = _item_kwargs(record["display"])
    volume = _item_kwargs(display.pop("volume"))
    del volume["auto_weight"]
    if volume["colors"] is None:
        del volume["colors"]
    stage.dates, stage.opens, stage.highs, stage.lows, stage.closes = (
        np.asarray(data[name], dtype=float) for name in ("dates", "open", "high", "low", "close")
    )
    stage.volume = np.asarray(data["volume"] if data["volume"] is not None else [], dtype=float)
    stage._index_is_default = data["index"] is None
    stage.index = (
        np.arange(len(stage.dates)) if stage._index_is_default else np.asarray(data["index"], dtype=object)
    )
    with stage:
        item = PlotCandleStick(
            stage.context, dates=stage.dates, opens=stage.opens, highs=stage.highs,
            lows=stage.lows, closes=stage.closes, volumes=stage.volume, time_counts=data["time_counts"],
            volume_kwargs=volume, time_formatter="auto", **display,
        )
    stage.candlestick_plot = item
    adapter = _CandleSeriesAdapter(item, stage)
    stage.register_time_series(record["id"], adapter, in_gap=record["in_gap"], mutation_adapter=adapter)


def _restore_econometric(stage, record):
    display = _item_kwargs(record["display"])
    data = record["data"]
    item = PlotEconometricSeries(stage.context, parent=stage, dates=data["dates"],
                                 values=data["values"], **display)
    stage.register_time_series(record["id"], item, in_gap=record["in_gap"])


def _restore_bars(stage, record):
    data = record["data"]
    display = _item_kwargs(record["display"])
    y_axis = display.pop("y_axis")
    stage.horizontal_bars = dcg.PlotColorBars(
        stage.context, parent=stage, X=data["lengths"], Y=data["levels"], horizontal=True,
        axes=(dcg.Axis.X1, y_axis), **display,
    )
    stage._horizontal_bars_id = record["id"]


def _restore_sma(stage, record):
    display = _item_kwargs(record["display"])
    stage.indicator_manager.create(
        type="SMA", instance_id=record["id"], **record["parameters"], **display,
    )


def _restore_range_box(stage, record):
    stage.register_tool(RangeBoxTool(
        stage, tool_id=record["id"], geometry=RangeBoxGeometry(**record["geometry"]),
        **record["options"], **_item_kwargs(record["display"]),
    ))


_SERIES_RESTORE = {"candles": _restore_candles, "econometric": _restore_econometric,
                   "horizontal-bars": _restore_bars}
_INDICATOR_RESTORE = {"sma": _restore_sma}
_DRAWING_RESTORE = {"range-box": _restore_range_box}


def _prepare(chart, stage, document):
    view = document["chart"]
    time = view["time"]
    stage._vectorized_collapse = time["vectorized"]
    stage._anchor_tooltips_enabled = view["anchor_tooltips_enabled"]
    stage.date_context_max_gap_px = chart.date_context_max_gap_px
    stage.date_context_min_spacing_px = chart.date_context_min_spacing_px
    stage._time_locator.measure_text_width_px = chart._time_locator.measure_text_width_px
    for collection, handlers in (
        ("series", _SERIES_RESTORE), ("indicators", _INDICATOR_RESTORE), ("drawings", _DRAWING_RESTORE),
    ):
        for record in document[collection]:
            try:
                handlers[record["kind"]](stage, record)
            except (TypeError, ValueError, RuntimeError, OverflowError) as exc:
                raise ChartPersistenceError(f"{collection} {record['id']!r}: {exc}") from exc

    stage._collapse_source_id = source_id = time["source"]
    source_dates = None if source_id is None else stage._plot_dates_by_id[source_id]
    manager = stage._gap_manager
    manager.reset(source_dates)
    interval = time["stream_interval"]
    if interval is not None:
        stage._stream_cadences[source_id] = float(interval)
        manager.stream_interval = float(interval)
        manager.stream_source_id = source_id
    if time["gaps"] is not None:
        manager.time_map = GapCollapsedTimeMap.from_gap_definitions(
            np.sort(source_dates), (tuple(map(float, gap)) for gap in time["gaps"]),
            use_local_time=time["use_local_time"],
        )
        manager.time_is_collapsed = True
        manager.active_method = time["active_method"]
        for item_id, entry in stage._time_series.items():
            dates = manager.time_map.project_many(entry.series.source_dates, in_gap=entry.in_gap)
            entry.series.set_plot_dates(dates)
            stage._plot_dates_by_id[item_id] = dates.copy()
        if stage.candlestick_plot is not None:
            stage.dates = stage._plot_dates_by_id["candles"].copy()
        stage._refresh_registered_tools()

    if stage.candlestick_plot is not None:
        candle = next(record for record in document["series"] if record["kind"] == "candles")
        stage.candlestick_plot._volume_uses_default_weight = candle["display"]["volume"]["auto_weight"]

    # Prepare ticks before swapping objects; callbacks during later frames use the new locator.
    x_view = view["axes"]["X1"]
    if x_view["range"] is not None and x_view["enabled"] and x_view["scale"] == "TIME":
        stage.axes_resize_callback(None, None, [x_view["range"]])


def _managed_items(chart):
    items = [chart.candlestick_plot, chart.horizontal_bars]
    if chart.candlestick_plot is not None:
        items.append(chart.candlestick_plot._volume_bar_series)
    items.extend(chart.get_time_series(item_id) for item_id in chart.time_series_ids)
    items.extend(instance.series for instance in chart.indicator_instances.values())
    items.extend(tool._layer for tool in chart.tools if isinstance(tool, RangeBoxTool))
    items.extend(getattr(chart, name) for name in _DIAGNOSTICS)
    return {
        item for item in items if isinstance(item, dcg.baseItem)
        and (item.parent is chart or item.parent is None)
    }


def _publish_view(chart, stage, view):
    for name, settings in view["axes"].items():
        axis = getattr(chart, name)
        _configure(axis, {key: settings[key] for key in _AXIS_PRESENTATION if key != "scale"})
        axis.scale = dcg.AxisScale[settings["scale"]]
        axis.auto_fit = False
        if settings["range"] is None:
            axis.no_initial_fit = False
            axis.min, axis.max = (1.0, 10.0) if axis.scale == dcg.AxisScale.LOG10 else (0.0, 1.0)
        else:
            # On the custom build this cancels any pending initial fit.
            axis.no_initial_fit = True
            axis.min, axis.max = settings["range"]
    legend = view["legend"]
    chart.no_legend = not legend["show"]
    chart.legend_config.location = dcg.LegendLocation[legend["location"]]
    _configure(chart.legend_config, {name: legend[name] for name in LEGEND_FLAGS})
    time = view["time"]
    chart.use_local_time = time["use_local_time"]
    chart.use_24hour_clock = time["use_24_hour"]
    chart.use_ISO8601 = time["use_iso8601"]
    _configure(chart.X1, _properties(stage.X1, _TICKS))
    chart._sync_context_menu_state()


def _publish(chart, stage, view):
    with chart.parents_mutex:
        old_children = chart.children
        managed = _managed_items(chart)
        new_children = stage.children
        stage.children = []
        old_contents = _properties(chart, (*_CONTENTS, "_horizontal_bars_id"))
        old_axes = {name: _properties(getattr(chart, name), _AXIS_ROLLBACK) for name in AXES}
        unset_axes = [name for name in AXES if _range(getattr(chart, name)) is None]
        had_diagnostics = any(old_contents[name] is not None for name in _DIAGNOSTICS)
        if had_diagnostics:
            old_axes["Y2"].update(_properties(chart.Y2, _DIAGNOSTIC_AXIS))
        old_ticks = _properties(chart.X1, _TICKS)
        old_legend = _properties(chart.legend_config, _LEGEND)
        old_plot = _properties(chart, (*_NATIVE_TIME, "no_legend"))
        old_menu = {key: chart._context_menu_items[key].value for key in
                    ("collapse", "vectorized", "source", "date_labels", "date_debug", "overlap")}
        try:
            chart.children = [child for child in old_children if child not in managed] + new_children
            _configure(chart, _properties(stage, (*_CONTENTS, "_horizontal_bars_id")))
            chart._indicator_manager.chart = chart
            if chart.candlestick_plot is not None:
                chart._time_series["candles"].series.chart = chart
            for tool in chart.tools:
                tool._chart = chart
            if had_diagnostics:
                _configure(chart.Y2, _properties(stage.Y2, _DIAGNOSTIC_AXIS))
            _publish_view(chart, stage, view)
        except Exception as exc:
            try:
                chart.children = old_children
                _configure(chart, old_contents)
                for name, settings in old_axes.items():
                    _configure(getattr(chart, name), settings)
                for name in unset_axes:
                    getattr(chart, name).fit()
                _configure(chart.X1, old_ticks)
                _configure(chart.legend_config, old_legend)
                _configure(chart, old_plot)
                for key, value in old_menu.items():
                    chart._context_menu_items[key].value = value
                stage.children = new_children
            except Exception as rollback_error:
                raise ChartPersistenceError(f"chart publication failed and rollback failed: {rollback_error}") from exc
            raise

        # Destructive cleanup starts only after the chart and its presentation commit.
        chart._anchor_tooltip_coordinator.clear()
        chart._set_cursor_tag_visible(False)
        chart.debug_text.value = ""
        for tool in old_contents["_tools"]:
            try:
                tool.dispose()
            except Exception:
                log.exception("Chart restored, but old drawing %r could not be disposed", tool.tool_id)
        for item in managed:
            try:
                if isinstance(item, (PlotCandleStick, PlotEconometricSeries)):
                    item._clear_active_tooltip()
                item.delete_item()
            except Exception:
                log.exception("Chart restored, but old item %r could not be disposed", item)
        for name, settings in view["axes"].items():
            if settings["range"] is None:
                getattr(chart, name).fit()
    chart.context.viewport.wake(full_refresh=True)


def restore_validated_chart(chart: DearCyFi, document: ChartDocument, *, publish=None) -> None:
    time = document["chart"]["time"]
    stage = DearCyFi(
        chart.context, attach=False, _snapshot_staging=True, prewarm=False,
        use_local_time=time["use_local_time"], use_24_hour=time["use_24_hour"],
        use_iso8601=time["use_iso8601"], apply_date_context_labels=time["date_context_labels"],
        max_density=chart._time_locator_max_density, char_px=chart._time_locator_char_px,
        font_path=chart._time_locator_font_path, font_size_px=chart._time_locator_font_size_px,
    )
    try:
        _prepare(chart, stage, document)
        if publish is None:
            _publish(chart, stage, document["chart"])
        else:
            publish(lambda: _publish(chart, stage, document["chart"]))
    finally:
        stage.delete_item()
    if chart.on_chart_restored is not None:
        try:
            chart.on_chart_restored(chart)
        except Exception:
            log.exception("Chart restored, but the host's on_chart_restored callback failed")
