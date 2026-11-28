import math
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import dearcygui as dcg
import numpy as np

from .PyTimeLocator import locator_time3
from .DCG_Candle_Utils import PlotCandleStick
from .candle_utils.gap_utils import GapCollapseManager
from .candle_indicators import CandleIndicatorManager
from .range_box_tools import AnchorTooltipCoordinator, InteractiveTool, RangeBoxDiagnosticSnapshot, RangeBoxGeometry, RangeBoxTool
from .streaming import classify_append_spacing, finite_timestamp, infer_cadence, latest_interval_matches


def _generate_sample_bar_data(num_bars, y_min, y_max, x_min, x_max):
    positions = np.linspace(y_min, y_max, num_bars)
    lengths = np.random.uniform(x_min, x_max, size=num_bars)
    return lengths, positions


def _horizontal_bar_weight(positions) -> float:
    values = np.sort(np.asarray(positions, dtype=float))
    if values.size > 1:
        spacing = np.diff(values)
        spacing = spacing[np.isfinite(spacing) & (spacing > 0)]
        if spacing.size:
            return float(np.min(spacing) * 0.95)
    return 0.1


@dataclass(frozen=True)
class TimeSeriesRegistration:
    series: object
    in_gap: str = "next"
    mutation_adapter: object | None = None


class _CandleSeriesAdapter:
    def __init__(self, candle: PlotCandleStick, chart: object | None = None) -> None:
        self.candle = candle
        self.chart = chart

    @property
    def source_dates(self) -> np.ndarray:
        return np.asarray(self.candle.source_dates, dtype=float)

    def set_plot_dates(self, dates: np.ndarray) -> None:
        self.candle.update(dates=np.asarray(dates, dtype=float))

    def set_plot_dates_incremental(self, dates: np.ndarray) -> None:
        self.candle.update(
            dates=np.asarray(dates, dtype=float),
            refresh_formatter=False,
            refresh_volume_weight=False,
        )

    def restore_source_dates(self) -> None:
        self.set_plot_dates(self.source_dates)

    def capture(self) -> dict[str, object]:
        return {
            "dates": np.asarray(self.candle.dates, dtype=float).copy(),
            "source_dates": self.source_dates,
            "opens": np.asarray(self.candle.opens, dtype=float).copy(),
            "highs": np.asarray(self.candle.highs, dtype=float).copy(),
            "lows": np.asarray(self.candle.lows, dtype=float).copy(),
            "closes": np.asarray(self.candle.closes, dtype=float).copy(),
            "volumes": np.asarray(self.candle.volumes, dtype=float).copy(),
            "time_counts": (
                []
                if self.candle.time_counts is None
                else [
                    [] if counts is None else list(counts)
                    for counts in self.candle.time_counts
                ]
            ),
        }

    def prepare_append(self, timestamp: float, values: dict[str, object]) -> dict[str, object]:
        prepared = self.capture()
        prepared["source_dates"] = np.append(prepared["source_dates"], timestamp)
        prepared["dates"] = np.append(prepared["dates"], timestamp)
        for field, value_name in (
            ("opens", "open"),
            ("highs", "high"),
            ("lows", "low"),
            ("closes", "close"),
            ("volumes", "volume"),
        ):
            prepared[field] = np.append(prepared[field], float(values[value_name]))
        if prepared["time_counts"]:
            prepared["time_counts"].append([])
        return prepared

    def prepare_update(self, values: dict[str, object]) -> dict[str, object]:
        prepared = self.capture()
        for field, value in values.items():
            array_name = "volumes" if field == "volume" else field + "s"
            prepared[array_name][-1] = float(value)
        return prepared

    def publish(self, prepared: dict[str, object]) -> None:
        self.candle.update_all(
            dates=prepared["dates"],
            opens=prepared["opens"],
            closes=prepared["closes"],
            lows=prepared["lows"],
            highs=prepared["highs"],
            volumes=prepared["volumes"],
            source_dates=prepared["source_dates"],
            time_counts=prepared["time_counts"],
            refresh_formatter=False,
            refresh_volume_weight=False,
        )


class _EconometricSeriesAdapter:
    def __init__(self, series) -> None:
        self.series = series

    def capture(self) -> dict[str, np.ndarray]:
        return {
            "dates": self.series.plot_dates,
            "source_dates": self.series.source_dates,
            "values": self.series.values,
        }

    def prepare_append(self, timestamp: float, values: dict[str, object]) -> dict[str, np.ndarray]:
        prepared = self.capture()
        prepared["source_dates"] = np.append(prepared["source_dates"], timestamp)
        prepared["dates"] = np.append(prepared["dates"], timestamp)
        prepared["values"] = np.append(prepared["values"], float(values["value"]))
        return prepared

    def prepare_update(self, values: dict[str, object]) -> dict[str, np.ndarray]:
        prepared = self.capture()
        prepared["values"][-1] = float(values["value"])
        return prepared

    def publish(self, prepared: dict[str, np.ndarray]) -> None:
        self.series.update_all(
            dates=prepared["dates"],
            values=prepared["values"],
            source_dates=prepared["source_dates"],
        )


class DearCyFi(dcg.Plot):
    """Reusable DearCyGui plot subclass with class-owned time-collapse behavior."""

    def __init__(
        self,
        context: dcg.Context,
        *,
        on_status=None,
        collapsed_time_cursor_tag: bool = True,
        cursor_tag_formatter: locator_time3.DateTimeSpec | Callable[[float], str] | None = None,
        cursor_tag_bullish_color=(0, 255, 0, 255),
        cursor_tag_bearish_color=(255, 0, 0, 255),
        cursor_tag_no_candle_color=(0, 0, 255, 255),
        use_local_time: bool = True,
        use_24_hour: bool = False,
        use_iso8601: bool = False,
        max_density: float = 0.5,
        char_px: float = 7.0,
        font_path: str | None = None,
        font_size_px: int = 17,
        prewarm: bool = True,
        apply_date_context_labels: bool = True,
        inject_boundary_ticks: bool | None = None,
        **plot_kwargs,
    ) -> None:
        super().__init__(context, **plot_kwargs)
        # use the plot kwargs to pass theme and other config from the DearCyFiDemo viewport initialization down to the plot
        # since the plot needs to know the theme for its time locator font loading logic.

        self._on_status = on_status

        print('loaded version with date context labels')

        self._time_locator_use_local_time = use_local_time
        self._time_locator_use_24_hour = use_24_hour
        self._time_locator_use_iso8601 = use_iso8601
        self._time_locator_max_density = max_density
        self._time_locator_char_px = char_px
        self._time_locator_font_size_px = font_size_px
        if inject_boundary_ticks is not None:
            apply_date_context_labels = bool(inject_boundary_ticks)

        if font_path is None:
            try:
                _dcg_font = Path(getattr(dcg, "__file__", "")).resolve().parent / "lmsans17-regular.otf"
                self._time_locator_font_path = str(_dcg_font) if _dcg_font.exists() else None
            except Exception:
                self._time_locator_font_path = None
        else:
            self._time_locator_font_path = font_path

        _measure = None
        if self._time_locator_font_path is not None:
            try:
                _measure = locator_time3.make_pil_text_width_measurer(
                    self._time_locator_font_path,
                    self._time_locator_font_size_px,
                )
                print(f"[DearCyFi] PIL text measurer enabled: {self._time_locator_font_path}")
            except Exception as exc:
                print(f"[DearCyFi] PIL measurer unavailable, falling back to char_px (reason: {exc})")

        self._time_locator = locator_time3.TimeAxisLocator(
            use_local_time=self._time_locator_use_local_time,
            use_24_hour=self._time_locator_use_24_hour,
            use_iso8601=self._time_locator_use_iso8601,
            max_density=self._time_locator_max_density,
            char_px=self._time_locator_char_px,
            measure_text_width_px=_measure,
            prewarm=prewarm,
        )

        self._gap_manager = GapCollapseManager()
        self._time_series: dict[str, TimeSeriesRegistration] = {}
        self._plot_dates_by_id: dict[str, np.ndarray] = {}
        self._time_series_sorted: dict[str, bool] = {}
        self._stream_cadences: dict[str, float] = {}
        self._collapse_source_id: str | None = None
        self._tools: list[InteractiveTool] = []
        self._tool_ids: set[str] = set()
        self._next_tool_number = 1
        self._indicator_manager = CandleIndicatorManager(self)
        self._anchor_tooltips_enabled = True
        self._anchor_tooltip_coordinator = AnchorTooltipCoordinator(self)
        self._last_resize_time_format_info: dict[str, object] = {}
        self._last_axis_resize_info: tuple[float, ...] | None = None
        self._cursor_tag_formatter = self._coerce_cursor_tag_formatter(cursor_tag_formatter)
        self._cursor_tag_bullish_color = dcg.color_as_int(cursor_tag_bullish_color)
        self._cursor_tag_bearish_color = dcg.color_as_int(cursor_tag_bearish_color)
        self._cursor_tag_no_candle_color = dcg.color_as_int(cursor_tag_no_candle_color)
        self._cursor_tag_enabled = False
        self._cursor_tag_handlers_installed = False
        self._cursor_tag_prior_no_mouse_pos = None
        self.cursor_tag = None

        self.time_format_level0: tuple = tuple(locator_time3.TIME_FORMAT_LEVEL0)
        self.time_format_level1: tuple = tuple(locator_time3.TIME_FORMAT_LEVEL1)
        self.time_format_level1_first: tuple = tuple(locator_time3.TIME_FORMAT_LEVEL1_FIRST)
        self.time_unit_range_cutoffs: tuple[float, ...] = (
            0.001,
            1.0,
            60.0,
            3600.0,
            86400.0,
            2629800.0,
            31557600.0,
            float(locator_time3.IMPLOT_MAX_TIME),
        )

        self.dates = np.array([])
        self.opens = np.array([])
        self.highs = np.array([])
        self.lows = np.array([])
        self.closes = np.array([])
        self.index = np.array([])
        self.volume = np.array([])
        self._index_is_default = True

        self.candlestick_plot = None
        self.horizontal_bars = None

        self.debug_text = dcg.SharedStr(context, value="")
        self._last_tick_counts: dict[str, int] = {}

        self._label_overlap_debug: bool = False
        self._apply_date_context_labels: bool = bool(apply_date_context_labels)
        self._date_context_debug: bool = False
        self._diag_extents_series = None
        self._diag_overlaps_series = None
        self._diag_date_context_series = None
        self.date_context_max_gap_px: float = 280.0
        self.date_context_min_spacing_px: float = 160.0
        self._vectorized_collapse: bool = True
        self._context_menu_items: dict[str, object] = {}
        self._context_menu_syncing: bool = False
        self._install_context_menu()

        self.X1.label = "Date"
        self.X1.scale = dcg.AxisScale.TIME
        self.Y1.label = "Price ($)"

        self.handlers += [
            dcg.AxesResizeHandler(context, callback=self.axes_resize_callback),
        ]
        self.cursor_tag_enabled = collapsed_time_cursor_tag

    @staticmethod
    def _default_cursor_tag_formatter() -> locator_time3.DateTimeSpec:
        return locator_time3.DateTimeSpec(locator_time3.DATE_DAY_MO_YR, locator_time3.TIMEFMT_HR_MIN)

    def _coerce_cursor_tag_formatter(
        self,
        formatter: locator_time3.DateTimeSpec | Callable[[float], str] | None,
    ) -> locator_time3.DateTimeSpec | Callable[[float], str]:
        if formatter is None:
            return self._default_cursor_tag_formatter()
        if isinstance(formatter, locator_time3.DateTimeSpec):
            return formatter
        if callable(formatter):
            return formatter
        raise TypeError("cursor_tag_formatter must be a DateTimeSpec, callable, or None")

    @property
    def vectorized_collapse(self) -> bool:
        return self._vectorized_collapse

    @vectorized_collapse.setter
    def vectorized_collapse(self, value: bool) -> None:
        self._vectorized_collapse = bool(value)
        self._sync_context_menu_state()

    @property
    def time_is_collapsed(self) -> bool:
        return bool(
            self._gap_manager.time_is_collapsed
            and self._gap_manager.time_map is not None
        )

    def _install_context_menu(self) -> None:
        if not hasattr(dcg, "Menu") or not hasattr(dcg, "MenuItem"):
            raise RuntimeError(
                "DearCyFi requires a custom DearCyGui build with plot context-menu "
                "support. Update DearCyGui to a build that allows Menu/MenuItem "
                "widgets to be attached to Plot."
            )
        probe = None  # tests for DearCyGui Menu/MenuItem support
        try:
            probe = dcg.Menu(self.context, parent=self, label="DearCyFi compatibility")
            probe.delete_item()

            collapse_item = dcg.MenuItem(
                self.context,
                parent=self,
                label="Collapse Time",
                check=True,
                value=False,
                callback=self._on_collapse_menu_action,
            )
            vectorized_item = dcg.MenuItem(
                self.context,
                parent=self,
                label="Vectorized Collapse",
                check=True,
                value=True,
                callback=self._on_vectorized_menu_action,
            )
            gaps_item = dcg.MenuItem(
                self.context,
                parent=self,
                label="Gaps n' Chunks",
                callback=self.add_gaps_chunks_GUI,
            )
            source_text = dcg.Text(
                self.context,
                parent=self,
                value="Collapse source: not selected",
            )
            with dcg.Menu(self.context, parent=self, label="Diagnostics"):
                date_labels_item = dcg.MenuItem(
                    self.context,
                    label="Date Context Labels",
                    check=True,
                    value=bool(self.apply_date_context_labels),
                    callback=self._on_date_labels_menu_action,
                )
                date_debug_item = dcg.MenuItem(
                    self.context,
                    label="Date Context Diagnostic",
                    check=True,
                    value=bool(self.date_context_debug),
                    callback=self._on_date_debug_menu_action,
                )
                overlap_item = dcg.MenuItem(
                    self.context,
                    label="Label Overlap Diagnostic",
                    check=True,
                    value=bool(self.label_overlap_debug),
                    callback=self._on_overlap_debug_menu_action,
                )
        except (AttributeError, TypeError, RuntimeError) as exc:
            raise RuntimeError(
                "DearCyFi requires a custom DearCyGui build with plot context-menu "
                "support. Update DearCyGui to a build that allows Menu/MenuItem "
                "widgets to be attached to Plot."
            ) from exc

        self._context_menu_items = {
            "collapse": collapse_item,
            "vectorized": vectorized_item,
            "gaps": gaps_item,
            "source": source_text,
            "diagnostics": date_debug_item.parent,
            "date_labels": date_labels_item,
            "date_debug": date_debug_item,
            "overlap": overlap_item,
        }
        self._context_menu_tooltips = {}
        self._add_context_menu_tooltip(
            "collapse",
            "Remove large time gaps from the chart. Uncheck to restore the original time coordinates.",
        )
        self._add_context_menu_tooltip(
            "vectorized",
            "Choose the faster vectorized or scalar method for the next collapse. This does not change an active collapse.",
        )
        self._add_context_menu_tooltip(
            "gaps",
            "Report gaps and contiguous chunks in the selected collapse source.",
        )
        self._add_context_menu_tooltip(
            "source",
            "The registered time series currently used to detect gaps for time collapse.",
        )
        self._add_context_menu_tooltip(
            "diagnostics",
            "Open settings for date-context labels and chart-label diagnostics.",
        )
        self._add_context_menu_tooltip(
            "date_labels",
            "Add sparse date context to the chart's existing x-axis labels.",
        )
        self._add_context_menu_tooltip(
            "date_debug",
            "Show the date-context label diagnostic overlay.",
        )
        self._add_context_menu_tooltip(
            "overlap",
            "Show detected x-axis label extents and overlaps.",
        )
        self._sync_context_menu_state()

    def _add_context_menu_tooltip(self, item_name: str, message: str) -> None:
        target = self._context_menu_items[item_name]
        with dcg.Tooltip(
            self.context,
            target=target,
            parent=self.parent,
        ) as tooltip:
            dcg.Text(self.context, value=message)
        self._context_menu_tooltips[item_name] = tooltip

    # DearCyGui only forwards required positional callback arguments.
    def _on_collapse_menu_action(self, _sender, _target, checked: bool) -> None:
        if self._context_menu_syncing:
            return
        if checked:
            if self._vectorized_collapse:
                self.collapse_time_chart_vec(debug=True)
            else:
                self.collapse_time_chart(debug=True)
        else:
            self.restore_time_chart()
        self._sync_context_menu_state()

    def _on_vectorized_menu_action(self, _sender, _target, checked: bool) -> None:
        if self._context_menu_syncing:
            return
        self.vectorized_collapse = checked

    def _on_date_labels_menu_action(self, _sender, _target, checked: bool) -> None:
        if not self._context_menu_syncing:
            self.apply_date_context_labels = checked

    def _on_date_debug_menu_action(self, _sender, _target, checked: bool) -> None:
        if not self._context_menu_syncing:
            self.date_context_debug = checked

    def _on_overlap_debug_menu_action(self, _sender, _target, checked: bool) -> None:
        if not self._context_menu_syncing:
            self.label_overlap_debug = checked

    def _sync_context_menu_state(self) -> None:
        if not getattr(self, "_context_menu_items", None):
            return
        self._context_menu_syncing = True
        try:
            self._context_menu_items["collapse"].value = self.time_is_collapsed
            self._context_menu_items["vectorized"].value = self._vectorized_collapse
            self._context_menu_items["source"].value = (
                f"Collapse source: {self._collapse_source_id or 'not selected'}"
            )
            self._context_menu_items["date_labels"].value = bool(
                self.apply_date_context_labels
            )
            self._context_menu_items["date_debug"].value = bool(
                self.date_context_debug
            )
            self._context_menu_items["overlap"].value = bool(
                self.label_overlap_debug
            )
        finally:
            self._context_menu_syncing = False

    def _install_cursor_tag_handlers(self) -> None:
        if self._cursor_tag_handlers_installed:
            return
        self.handlers += [
            dcg.MouseMoveHandler(self.context, callback=self._handle_cursor_tag_mouse_move),
        ]
        self._cursor_tag_handlers_installed = True

    def _ensure_cursor_tag(self) -> None:
        if self.cursor_tag is not None:
            return
        with self.X1:
            self.cursor_tag = dcg.AxisTag(
                self.context,
                coord=0.0,
                text="",
                bg_color=self._cursor_tag_no_candle_color,
            )
        self.cursor_tag.show = False

    def _set_cursor_tag_visible(self, visible: bool) -> None:
        if self.cursor_tag is not None:
            self.cursor_tag.show = bool(visible)

    @property
    def cursor_tag_enabled(self) -> bool:
        return self._cursor_tag_enabled

    @cursor_tag_enabled.setter
    def cursor_tag_enabled(self, value: bool) -> None:
        enabled = bool(value)
        if enabled == self._cursor_tag_enabled:
            return
        self._cursor_tag_enabled = enabled
        if enabled:
            self._install_cursor_tag_handlers()
            self._ensure_cursor_tag()
            self._cursor_tag_prior_no_mouse_pos = bool(getattr(self, "no_mouse_pos", False))
            self.no_mouse_pos = True
        else:
            self._set_cursor_tag_visible(False)
            if self._cursor_tag_prior_no_mouse_pos is not None:
                self.no_mouse_pos = bool(self._cursor_tag_prior_no_mouse_pos)
                self._cursor_tag_prior_no_mouse_pos = None

    @property
    def cursor_tag_formatter(self) -> locator_time3.DateTimeSpec | Callable[[float], str]:
        return self._cursor_tag_formatter

    @cursor_tag_formatter.setter
    def cursor_tag_formatter(self, value: locator_time3.DateTimeSpec | Callable[[float], str] | None) -> None:
        self._cursor_tag_formatter = self._coerce_cursor_tag_formatter(value)

    @property
    def cursor_tag_bullish_color(self):
        return self._cursor_tag_bullish_color

    @cursor_tag_bullish_color.setter
    def cursor_tag_bullish_color(self, value) -> None:
        self._cursor_tag_bullish_color = dcg.color_as_int(value)

    @property
    def cursor_tag_bearish_color(self):
        return self._cursor_tag_bearish_color

    @cursor_tag_bearish_color.setter
    def cursor_tag_bearish_color(self, value) -> None:
        self._cursor_tag_bearish_color = dcg.color_as_int(value)

    @property
    def cursor_tag_no_candle_color(self):
        return self._cursor_tag_no_candle_color

    @cursor_tag_no_candle_color.setter
    def cursor_tag_no_candle_color(self, value) -> None:
        self._cursor_tag_no_candle_color = dcg.color_as_int(value)
        if self.cursor_tag is not None and not self.cursor_tag.show:
            self.cursor_tag.bg_color = self._cursor_tag_no_candle_color

    def _set_status(self, message: str) -> None:
        if callable(self._on_status):
            self._on_status(str(message))

    def expand_cursor_plot_x_to_real_time(self, x_coord: float) -> float:
        """Expand a plot coordinate with the boundary clamps used by drawing tools."""
        x_value = float(x_coord)
        if not np.isfinite(x_value):
            raise ValueError("cursor x coordinate must be finite")
        if self._gap_manager.time_is_collapsed and self._gap_manager.time_map is not None:
            return float(self._gap_manager.time_map.expand(x_value))
        return x_value

    def format_cursor_timestamp(self, real_timestamp: float) -> str:
        timestamp = float(real_timestamp)
        if not np.isfinite(timestamp):
            raise ValueError("cursor timestamp must be finite")
        formatter = self._cursor_tag_formatter
        if isinstance(formatter, locator_time3.DateTimeSpec):
            use_24_hour = bool(self._time_locator_use_24_hour or getattr(formatter, "use_24_hour", False))
            use_iso8601 = bool(self._time_locator_use_iso8601 or getattr(formatter, "use_iso8601", False))
            return locator_time3.format_datetime(
                locator_time3.ImPlotTime.from_double(timestamp),
                formatter,
                use_local_time=self._time_locator_use_local_time,
                use_24_hour=use_24_hour,
                use_iso8601=use_iso8601,
            )
        text = formatter(timestamp)
        if not isinstance(text, str):
            raise TypeError("cursor_tag_formatter callable must return a string")
        return text

    def _cursor_tag_timestamp_and_text(self, x: float) -> tuple[float, str]:
        if not math.isfinite(x):
            raise ValueError("cursor x coordinate must be finite")
        timestamp = self._expand_x_axis_time(x)
        return timestamp, self.format_cursor_timestamp(timestamp)

    def format_cursor_tag_text_for_plot_x(self, x_coord: float) -> str:
        return self._cursor_tag_timestamp_and_text(float(x_coord))[1]

    def get_cursor_tag_state_for_plot_x(self, x_coord: float) -> dict[str, object]:
        x_value = float(x_coord)
        timestamp, text = self._cursor_tag_timestamp_and_text(x_value)
        bg_color = self._cursor_tag_no_candle_color
        if self.candlestick_plot is not None:
            direction = self.candlestick_plot.get_candle_direction_for_x(x_value)
            if direction == "bullish":
                bg_color = self._cursor_tag_bullish_color
            elif direction == "bearish":
                bg_color = self._cursor_tag_bearish_color
        return {
            "coord": x_value,
            "real_timestamp": timestamp,
            "text": text,
            "bg_color": bg_color,
        }

    def _update_cursor_tag_from_plot_x(self, x_coord: float) -> None:
        if not self._cursor_tag_enabled:
            return
        x_value = float(x_coord)
        if not np.isfinite(x_value):
            self._set_cursor_tag_visible(False)
            return
        self._ensure_cursor_tag()
        state = self.get_cursor_tag_state_for_plot_x(x_value)
        self.cursor_tag.coord = state["coord"]
        self.cursor_tag.text = state["text"]
        self.cursor_tag.bg_color = state["bg_color"]
        self._set_cursor_tag_visible(True)

    def _cursor_is_inside_plot(self, x_coord: float, y_coord: float) -> bool:
        x_value = float(x_coord)
        y_value = float(y_coord)
        if not np.isfinite(x_value) or not np.isfinite(y_value):
            return False
        x_min, x_max = sorted((float(self.X1.min), float(self.X1.max)))
        y_min, y_max = sorted((float(self.Y1.min), float(self.Y1.max)))
        return x_min <= x_value <= x_max and y_min <= y_value <= y_max

    def _handle_cursor_tag_mouse_move(self, *_args) -> None:
        x_coord = float(self.X1.mouse_coord)
        y_coord = float(self.Y1.mouse_coord)
        if not self._cursor_is_inside_plot(x_coord, y_coord):
            self._set_cursor_tag_visible(False)
            self.context.viewport.wake(full_refresh=True)
            return
        self._update_cursor_tag_from_plot_x(x_coord)
        self.context.viewport.wake(full_refresh=True)

    @property
    def time_series_ids(self) -> tuple[str, ...]:
        return tuple(self._time_series)

    @property
    def tools(self) -> tuple[InteractiveTool, ...]:
        return tuple(self._tools)

    @property
    def boxes(self) -> tuple[RangeBoxTool, ...]:
        return tuple(tool for tool in self._tools if isinstance(tool, RangeBoxTool))

    @property
    def anchor_tooltips_enabled(self) -> bool:
        return self._anchor_tooltips_enabled

    @anchor_tooltips_enabled.setter
    def anchor_tooltips_enabled(self, value: bool) -> None:
        self._anchor_tooltips_enabled = bool(value)
        if not self._anchor_tooltips_enabled:
            self._anchor_tooltip_coordinator.clear()

    @property
    def collapse_source_id(self) -> str | None:
        return self._collapse_source_id

    @collapse_source_id.setter
    def collapse_source_id(self, series_id: str | None) -> None:
        if series_id is not None and series_id not in self._time_series:
            raise ValueError(f"Unknown collapse source ID: {series_id!r}")
        if series_id == self._collapse_source_id:
            return
        self.restore_time_chart()
        self._collapse_source_id = series_id
        self._sync_context_menu_state()

    def register_time_series(
        self,
        series_id: str,
        series,
        *,
        in_gap: str = "next",
        replace: bool = False,
        mutation_adapter: object | None = None,
    ) -> None:
        """Register a source-date projection and, optionally, mutation support.

        Mutation adapters implement ``capture()``, ``prepare_append(timestamp,
        values)``, ``prepare_update(values)``, and ``publish(prepared)``. A
        registration without that capability remains a valid collapse follower.
        """
        if not isinstance(series_id, str) or not series_id:
            raise ValueError("series_id must be a non-empty string")
        if in_gap not in {"next", "previous"}:
            raise ValueError("in_gap must be 'next' or 'previous'")
        if series_id in self._time_series and not replace:
            raise ValueError(f"Time series ID is already registered: {series_id!r}")
        if not hasattr(series, "source_dates"):
            raise TypeError("registered series must expose source_dates")
        if not callable(getattr(series, "set_plot_dates", None)):
            raise TypeError("registered series must implement set_plot_dates(dates)")
        if not callable(getattr(series, "restore_source_dates", None)):
            raise TypeError("registered series must implement restore_source_dates()")
        if mutation_adapter is not None and not all(
            callable(getattr(mutation_adapter, method, None))
            for method in ("capture", "prepare_append", "prepare_update", "publish")
        ):
            raise TypeError(
                "mutation_adapter must implement capture, prepare_append, prepare_update, and publish"
            )
        if (
            mutation_adapter is None
            and hasattr(series, "values")
            and hasattr(series, "plot_dates")
            and callable(getattr(series, "update_all", None))
        ):
            mutation_adapter = _EconometricSeriesAdapter(series)

        if replace and series_id in self._time_series:
            self.restore_time_chart()
            self._stream_cadences.pop(series_id, None)
        source_dates = np.asarray(series.source_dates, dtype=float)
        self._time_series[series_id] = TimeSeriesRegistration(series, in_gap, mutation_adapter)
        self._plot_dates_by_id[series_id] = source_dates.copy()
        self._time_series_sorted[series_id] = bool(
            source_dates.size < 2 or np.all(np.diff(source_dates) >= 0)
        )
        self._sync_context_menu_state()

    @property
    def indicator_manager(self):
        return self._indicator_manager

    @property
    def indicator_instances(self) -> dict[str, object]:
        return self._indicator_manager.instances

    @property
    def indicator_ids(self) -> tuple[str, ...]:
        return self._indicator_manager.indicator_ids

    def create_indicator(
        self,
        *,
        type: str = "SMA",
        period: object = 20,
        field: str = "close",
        y_axis: dcg.Axis = dcg.Axis.Y1,
        **kwargs,
    ):
        return self._indicator_manager.create(
            type=type,
            period=period,
            field=field,
            y_axis=y_axis,
            **kwargs,
        )

    add_indicator = create_indicator

    def edit_indicator(self, instance_id: str, *, period: object, field: str):
        return self._indicator_manager.edit(instance_id, period=period, field=field)

    def remove_indicator(self, instance_id: str) -> None:
        self._indicator_manager.remove(instance_id)

    def _stream_interval(self, series_id: str, *, cache: bool = True) -> float:
        if series_id in self._stream_cadences:
            return self._stream_cadences[series_id]
        registration = self._time_series[series_id]
        cadence = infer_cadence(registration.series.source_dates)
        if cache:
            self._stream_cadences[series_id] = cadence
        return cadence

    def check_last_sample(self, series_id: str, timestamp: float) -> tuple[bool, float | None]:
        if series_id not in self._time_series:
            raise ValueError(f"Unknown time series ID: {series_id!r}")
        candidate = finite_timestamp(timestamp)
        dates = np.asarray(self._time_series[series_id].series.source_dates, dtype=float)
        if dates.size == 0:
            return False, None
        cadence = self._stream_interval(series_id)
        latest = float(dates[-1])
        return latest_interval_matches(latest, candidate, cadence), latest

    @staticmethod
    def _normalize_sample_values(series_id: str, values: dict[str, object], *, append: bool) -> dict[str, float]:
        if series_id == "candles":
            allowed = {"open", "high", "low", "close", "volume"}
            unknown = set(values) - allowed
            if unknown:
                raise ValueError(f"Unsupported candle field(s): {', '.join(sorted(unknown))}")
            if append:
                missing = {"open", "high", "low", "close"} - set(values)
                if missing:
                    raise ValueError(f"Missing candle field(s): {', '.join(sorted(missing))}")
            if not append and not values:
                raise ValueError("Latest update requires at least one field")
            normalized = {}
            for name, value in values.items():
                if value is None:
                    raise ValueError(f"{name} must be a finite number")
                try:
                    number = float(value)
                except (TypeError, ValueError, OverflowError) as exc:
                    raise ValueError(f"{name} must be a finite number") from exc
                if not np.isfinite(number):
                    raise ValueError(f"{name} must be a finite number")
                normalized[name] = number
            if append and "volume" not in normalized:
                normalized["volume"] = 0.0
            return normalized
        if set(values) != {"value"} or values["value"] is None:
            raise ValueError("Scalar econometric samples require exactly one numeric 'value' field")
        try:
            return {"value": float(values["value"])}
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("value must be numeric") from exc

    @staticmethod
    def _validate_candle_arrays(prepared: dict[str, object]) -> None:
        values = [float(prepared[name][-1]) for name in ("opens", "highs", "lows", "closes", "volumes")]
        open_value, high_value, low_value, close_value, volume_value = values
        if not all(np.isfinite(value) for value in values):
            raise ValueError("Candle OHLCV values must be finite")
        if volume_value < 0:
            raise ValueError("Candle volume must be non-negative")
        if not (low_value <= open_value <= high_value and low_value <= close_value <= high_value):
            raise ValueError("Candle values must satisfy low <= open/close <= high")

    def _publish_stream_mutation(
        self,
        series_id: str,
        adapter,
        prepared: dict[str, object],
        *,
        new_timestamp: float | None,
        spacing: str | None,
        cadence: float,
    ) -> None:
        registration = self._time_series[series_id]
        source_id = self._collapse_source_id
        selected_source_append = new_timestamp is not None and series_id == source_id
        old_manager = (
            self._gap_manager.dates_real,
            self._gap_manager.time_is_collapsed,
            self._gap_manager.time_map,
            self._gap_manager.stream_source_id,
            self._gap_manager.stream_interval,
        )
        old_cadences = dict(self._stream_cadences)
        old_plot_dates = {
            key: value.copy() for key, value in self._plot_dates_by_id.items()
        }
        old_sorted = dict(self._time_series_sorted)
        old_chart_state = {
            "dates": self.dates.copy(),
            "opens": self.opens.copy(),
            "highs": self.highs.copy(),
            "lows": self.lows.copy(),
            "closes": self.closes.copy(),
            "volume": self.volume.copy(),
            "index": self.index.copy(),
        }
        old_axis_labels = (
            list(self.X1.labels),
            list(self.X1.labels_coord),
            list(self.X1.labels_major),
            self.X1.keep_default_ticks,
            self.X1.no_gridlines,
        )
        old_adapter_data = adapter.capture()
        candidate_dates: dict[str, np.ndarray] = {}
        previous_source_timestamp = None
        candidate_map = self._gap_manager.time_map
        map_snapshot = None

        if new_timestamp is not None:
            current_source_dates = np.asarray(registration.series.source_dates, dtype=float)
            if current_source_dates.size == 0:
                raise ValueError("Cannot append to an empty series")
            current_plot_dates = self._plot_dates_by_id.get(
                series_id,
                np.asarray(registration.series.source_dates, dtype=float),
            )
            if selected_source_append:
                previous_source_timestamp = float(current_source_dates[-1])
                if self._gap_manager.time_is_collapsed:
                    if self._gap_manager.time_map is None:
                        raise RuntimeError("Collapsed chart has no time map")
                    plotted_timestamp = self._gap_manager.time_map.project_tail_append(
                        timestamp=new_timestamp,
                        interval=cadence,
                        spacing=spacing,
                        query=new_timestamp,
                        in_gap="next",
                    )
                else:
                    plotted_timestamp = new_timestamp
                candidate_dates[series_id] = np.append(current_plot_dates, plotted_timestamp)
                if self._gap_manager.time_is_collapsed and spacing == "gap":
                    for follower_id, follower in self._time_series.items():
                        if follower_id == series_id:
                            continue
                        source_dates = np.asarray(follower.series.source_dates, dtype=float)
                        old_dates = old_plot_dates.get(follower_id, source_dates)
                        if self._time_series_sorted.get(follower_id, False):
                            suffix_start = int(
                                np.searchsorted(source_dates, previous_source_timestamp, side="right")
                            )
                            affected = slice(suffix_start, None)
                            affected_sources = source_dates[suffix_start:]
                        else:
                            affected = source_dates > previous_source_timestamp
                            affected_sources = source_dates[affected]
                        projected = candidate_map.project_tail_append_many(
                            timestamp=new_timestamp,
                            interval=cadence,
                            spacing=spacing,
                            queries=affected_sources,
                            in_gap=follower.in_gap,
                        )
                        next_dates = old_dates.copy()
                        next_dates[affected] = projected
                        candidate_dates[follower_id] = next_dates
            else:
                plotted_timestamp = new_timestamp
                if self._gap_manager.time_is_collapsed and self._gap_manager.time_map is not None:
                    plotted_timestamp = float(self._gap_manager.time_map.project(
                        new_timestamp,
                        in_gap=registration.in_gap,
                    ))
                candidate_dates[series_id] = np.append(current_plot_dates, plotted_timestamp)
            prepared["dates"] = candidate_dates[series_id]
            if series_id == "candles":
                prepared["source_dates"] = np.append(current_source_dates, new_timestamp)
        else:
            candidate_dates[series_id] = np.asarray(prepared["dates"], dtype=float).copy()

        prepared_indicator_states = None
        if series_id == "candles" and self._indicator_manager.indicator_ids:
            prepared_indicator_states = self._indicator_manager.prepare_candle_state(prepared)

        manager_dates = old_manager[0]
        if selected_source_append and (
            self._gap_manager.stream_source_id not in (None, series_id)
            or manager_dates is None
            or manager_dates.size == 0
            or float(manager_dates[-1]) != previous_source_timestamp
        ):
            manager_dates = np.asarray(registration.series.source_dates, dtype=float).copy()

        rollback_errors: list[Exception] = []
        try:
            if selected_source_append:
                self._gap_manager.dates_real = manager_dates
                self._gap_manager.stream_source_id = series_id
                self._gap_manager.stream_interval = cadence
                map_snapshot = self._gap_manager.append_source_timestamp(
                    new_timestamp,
                    source_id=series_id,
                    interval=cadence,
                    spacing=spacing,
                    use_local_time=self._time_locator_use_local_time,
                )
            adapter.publish(prepared)
            if series_id == "candles" and prepared_indicator_states is not None:
                self._indicator_manager.publish_candle_state(
                    prepared,
                    prepared_results=prepared_indicator_states,
                )
            for follower_id, projected in candidate_dates.items():
                if follower_id == series_id:
                    self._plot_dates_by_id[follower_id] = projected.copy()
                    continue
                follower_registration = self._time_series[follower_id]
                incremental_setter = getattr(
                    follower_registration.mutation_adapter,
                    "set_plot_dates_incremental",
                    None,
                )
                if (
                    selected_source_append
                    and self._gap_manager.time_is_collapsed
                    and spacing == "gap"
                    and callable(incremental_setter)
                ):
                    incremental_setter(projected)
                else:
                    follower_registration.series.set_plot_dates(projected)
                self._plot_dates_by_id[follower_id] = projected.copy()
            if selected_source_append and self._gap_manager.time_is_collapsed and spacing == "gap":
                self._refresh_registered_tools()
            if "candles" in candidate_dates:
                self.dates = candidate_dates["candles"].copy()
            if series_id == "candles":
                self.opens = np.asarray(prepared["opens"], dtype=float).copy()
                self.highs = np.asarray(prepared["highs"], dtype=float).copy()
                self.lows = np.asarray(prepared["lows"], dtype=float).copy()
                self.closes = np.asarray(prepared["closes"], dtype=float).copy()
                self.volume = np.asarray(prepared["volumes"], dtype=float).copy()
                if new_timestamp is not None:
                    next_index = len(self.index) if self._index_is_default else new_timestamp
                    self.index = np.append(self.index, next_index)
            if (
                selected_source_append
                and self._gap_manager.time_is_collapsed
                and self._last_axis_resize_info is not None
            ):
                self.axes_resize_callback(None, None, [self._last_axis_resize_info])
            self.context.viewport.wake(full_refresh=True)
        except Exception as original_error:
            if map_snapshot is not None and old_manager[2] is not None:
                try:
                    old_manager[2].rollback_source_append(map_snapshot)
                except Exception as exc:
                    rollback_errors.append(exc)
            try:
                adapter.publish(old_adapter_data)
            except Exception as exc:
                rollback_errors.append(exc)
            if series_id == "candles" and prepared_indicator_states is not None:
                try:
                    self._indicator_manager.publish_candle_state(old_adapter_data)
                except Exception as exc:
                    rollback_errors.append(exc)
            for follower_id in candidate_dates:
                if follower_id == series_id:
                    continue
                original_dates = old_plot_dates[follower_id]
                try:
                    follower_registration = self._time_series[follower_id]
                    incremental_setter = getattr(
                        follower_registration.mutation_adapter,
                        "set_plot_dates_incremental",
                        None,
                    )
                    if callable(incremental_setter):
                        incremental_setter(original_dates)
                    else:
                        follower_registration.series.set_plot_dates(original_dates)
                except Exception as exc:
                    rollback_errors.append(exc)
            (
                self._gap_manager.dates_real,
                self._gap_manager.time_is_collapsed,
                self._gap_manager.time_map,
                self._gap_manager.stream_source_id,
                self._gap_manager.stream_interval,
            ) = old_manager
            self._stream_cadences = old_cadences
            self._plot_dates_by_id = old_plot_dates
            self._time_series_sorted = old_sorted
            self.dates = old_chart_state["dates"]
            self.opens = old_chart_state["opens"]
            self.highs = old_chart_state["highs"]
            self.lows = old_chart_state["lows"]
            self.closes = old_chart_state["closes"]
            self.volume = old_chart_state["volume"]
            self.index = old_chart_state["index"]
            try:
                (
                    self.X1.labels,
                    self.X1.labels_coord,
                    self.X1.labels_major,
                    self.X1.keep_default_ticks,
                    self.X1.no_gridlines,
                ) = old_axis_labels
            except Exception as exc:
                rollback_errors.append(exc)
            if self._gap_manager.time_is_collapsed:
                try:
                    self._refresh_registered_tools()
                except Exception as exc:
                    rollback_errors.append(exc)
            if rollback_errors:
                raise RuntimeError(
                    "Streaming mutation failed and one or more rollback steps also failed: "
                    + "; ".join(str(error) for error in rollback_errors)
                ) from original_error
            raise

        self._stream_cadences[series_id] = cadence
        if new_timestamp is not None:
            self._time_series_sorted[series_id] = True

    def append_sample(self, series_id: str, *, timestamp: float, **values) -> None:
        if series_id not in self._time_series:
            raise ValueError(f"Unknown time series ID: {series_id!r}")
        registration = self._time_series[series_id]
        adapter = registration.mutation_adapter
        if adapter is None:
            raise TypeError(f"Time series {series_id!r} does not support mutation")
        candidate = finite_timestamp(timestamp)
        cadence = self._stream_interval(series_id, cache=False)
        source_dates = np.asarray(registration.series.source_dates, dtype=float)
        if source_dates.size == 0:
            raise ValueError("Cannot append to an empty series")
        spacing = classify_append_spacing(float(source_dates[-1]), candidate, cadence)
        if spacing == "short":
            raise ValueError("Appended timestamp must be at least one cached interval after the latest sample")
        normalized = self._normalize_sample_values(series_id, values, append=True)
        prepared = adapter.prepare_append(candidate, normalized)
        if series_id == "candles":
            self._validate_candle_arrays(prepared)
        self._publish_stream_mutation(
            series_id,
            adapter,
            prepared,
            new_timestamp=candidate,
            spacing=spacing,
            cadence=cadence,
        )

    def update_last_sample(self, series_id: str, **values) -> None:
        if series_id not in self._time_series:
            raise ValueError(f"Unknown time series ID: {series_id!r}")
        registration = self._time_series[series_id]
        adapter = registration.mutation_adapter
        if adapter is None:
            raise TypeError(f"Time series {series_id!r} does not support mutation")
        cadence = self._stream_interval(series_id, cache=False)
        if np.asarray(registration.series.source_dates, dtype=float).size == 0:
            raise ValueError("Cannot update the latest value of an empty series")
        normalized = self._normalize_sample_values(series_id, values, append=False)
        prepared = adapter.prepare_update(normalized)
        if series_id == "candles":
            self._validate_candle_arrays(prepared)
        self._publish_stream_mutation(
            series_id,
            adapter,
            prepared,
            new_timestamp=None,
            spacing=None,
            cadence=cadence,
        )

    def check_last_candle(self, timestamp: float) -> tuple[bool, float | None]:
        return self.check_last_sample("candles", timestamp)

    def append_candle(
        self,
        *,
        timestamp: float,
        open: float,
        high: float,
        low: float,
        close: float,
        volume: float = 0.0,
    ) -> None:
        self.append_sample(
            "candles",
            timestamp=timestamp,
            open=open,
            high=high,
            low=low,
            close=close,
            volume=volume,
        )

    def update_last_candle(
        self,
        *,
        open: float | None = None,
        high: float | None = None,
        low: float | None = None,
        close: float | None = None,
        volume: float | None = None,
    ) -> None:
        values = {
            name: value
            for name, value in (
                ("open", open),
                ("high", high),
                ("low", low),
                ("close", close),
                ("volume", volume),
            )
            if value is not None
        }
        self.update_last_sample("candles", **values)

    def register_tool(self, tool: InteractiveTool) -> InteractiveTool:
        if not isinstance(tool, InteractiveTool):
            raise TypeError("tool must implement InteractiveTool")
        if tool.tool_id in self._tool_ids:
            raise ValueError(f"Tool ID is already registered: {tool.tool_id!r}")
        self._tools.append(tool)
        self._tool_ids.add(tool.tool_id)
        return tool

    def _refresh_registered_tools(self) -> None:
        for tool in self._tools:
            tool.refresh_projection()

    def _next_tool_id(self, tool_kind: str) -> str:
        while True:
            candidate = f"{tool_kind}-{self._next_tool_number}"
            self._next_tool_number += 1
            if candidate not in self._tool_ids:
                return candidate

    def _require_candles_loaded(self) -> PlotCandleStick:
        if self.candlestick_plot is None:
            raise RuntimeError("Cannot add a range box before candles are loaded")
        return self.candlestick_plot

    def _default_box_geometry(self) -> RangeBoxGeometry:
        candle_plot = self._require_candles_loaded()
        source_dates = np.asarray(candle_plot.source_dates, dtype=float)
        if source_dates.size == 0:
            raise RuntimeError("Cannot add a range box before candles are loaded")
        data_x_min = float(np.min(source_dates))
        data_x_max = float(np.max(source_dates))

        x_min_plot = float(self.X1.min)
        x_max_plot = float(self.X1.max)
        view_x_usable = np.isfinite(x_min_plot) and np.isfinite(x_max_plot) and x_min_plot != x_max_plot
        if view_x_usable:
            x_min_source = self.expand_cursor_plot_x_to_real_time(min(x_min_plot, x_max_plot))
            x_max_source = self.expand_cursor_plot_x_to_real_time(max(x_min_plot, x_max_plot))
        else:
            x_min_source = data_x_min
            x_max_source = data_x_max

        if x_min_source == x_max_source:
            cadence = 60.0
            if source_dates.size > 1:
                spacing = np.diff(source_dates)
                spacing = spacing[np.isfinite(spacing) & (spacing > 0)]
                if spacing.size:
                    cadence = float(np.median(spacing))
            center_time = float(source_dates[source_dates.size // 2])
            x_min_source = center_time - cadence * 2.0
            x_max_source = center_time + cadence * 2.0

        y_axis = candle_plot.y_axis
        y_axis_obj = getattr(self, y_axis.name)
        y_min_axis = float(y_axis_obj.min)
        y_max_axis = float(y_axis_obj.max)
        view_y_usable = np.isfinite(y_min_axis) and np.isfinite(y_max_axis) and y_min_axis != y_max_axis
        if view_y_usable:
            y_min = min(y_min_axis, y_max_axis)
            y_max = max(y_min_axis, y_max_axis)
        else:
            y_min = float(np.min(self.lows))
            y_max = float(np.max(self.highs))
        if y_min == y_max:
            y_min -= 1.0
            y_max += 1.0

        x_span = x_max_source - x_min_source
        y_span = y_max - y_min
        default_x_span = max(x_span * 0.2, 1.0)
        default_y_span = max(y_span * 0.2, 0.01)
        x_center = x_min_source + x_span * 0.5
        y_center = y_min + y_span * 0.5
        return RangeBoxGeometry(
            left_time=x_center - default_x_span * 0.5,
            bottom=y_center - default_y_span * 0.5,
            right_time=x_center + default_x_span * 0.5,
            top=y_center + default_y_span * 0.5,
        )

    def add_box(
        self,
        sender=None,
        app_data=None,
        user_data=None,
        *,
        tool_id: str | None = None,
        left_time: float | None = None,
        bottom: float | None = None,
        right_time: float | None = None,
        top: float | None = None,
        geometry: RangeBoxGeometry | None = None,
        y_axis: dcg.Axis | None = None,
        on_geometry_changing=None,
        on_geometry_committed=None,
        anchor_tooltips_enabled: bool | None = None,
        hit_size: float = 18.0,
        min_source_width: float = 1.0,
        min_source_height: float = 0.01,
    ) -> RangeBoxTool:
        candle_plot = self._require_candles_loaded()
        if geometry is not None and any(value is not None for value in (left_time, bottom, right_time, top)):
            raise ValueError("Specify either geometry or explicit box coordinates, not both")
        if geometry is None:
            explicit_values = (left_time, bottom, right_time, top)
            if all(value is None for value in explicit_values):
                geometry = self._default_box_geometry()
            elif any(value is None for value in explicit_values):
                raise ValueError("Explicit box creation requires left_time, bottom, right_time, and top")
            else:
                geometry = RangeBoxGeometry(
                    left_time=float(left_time),
                    bottom=float(bottom),
                    right_time=float(right_time),
                    top=float(top),
                )

        resolved_tool_id = self._next_tool_id("range-box") if tool_id is None else tool_id
        resolved_y_axis = candle_plot.y_axis if y_axis is None else y_axis
        resolved_anchor_tooltips = self.anchor_tooltips_enabled if anchor_tooltips_enabled is None else anchor_tooltips_enabled

        box = RangeBoxTool(
            self,
            tool_id=resolved_tool_id,
            geometry=geometry,
            y_axis=resolved_y_axis,
            on_geometry_changing=on_geometry_changing,
            on_geometry_committed=on_geometry_committed,
            anchor_tooltips_enabled=resolved_anchor_tooltips,
            hit_size=hit_size,
            min_source_width=min_source_width,
            min_source_height=min_source_height,
        )
        try:
            self.register_tool(box)
        except Exception:
            box.dispose()
            raise
        return box

    def remove_all_boxes(self) -> None:
        remaining_tools: list[InteractiveTool] = []
        remaining_ids: set[str] = set()
        for tool in self._tools:
            if isinstance(tool, RangeBoxTool):
                tool.dispose()
                continue
            remaining_tools.append(tool)
            remaining_ids.add(tool.tool_id)
        self._tools = remaining_tools
        self._tool_ids = remaining_ids

    def get_box_snapshots(self) -> tuple[RangeBoxDiagnosticSnapshot, ...]:
        return tuple(box.diagnostic_snapshot() for box in self.boxes)

    @staticmethod
    def _format_box_snapshot(snapshot: RangeBoxDiagnosticSnapshot) -> str:
        source = snapshot.source_geometry
        plot = snapshot.plot_geometry
        return (
            f"{snapshot.tool_id} ({snapshot.tool_kind})\n"
            f"  source: left={source.left_time:.3f} right={source.right_time:.3f} bottom={source.bottom:.4f} top={source.top:.4f}\n"
            f"  plot:   left={plot.left_time:.3f} right={plot.right_time:.3f} bottom={plot.bottom:.4f} top={plot.top:.4f}"
        )

    def print_boxes(self) -> str:
        snapshots = self.get_box_snapshots()
        if not snapshots:
            text = "No range boxes."
            print(text)
            self._set_status(text)
            return text
        text = "\n".join(self._format_box_snapshot(snapshot) for snapshot in snapshots)
        print(text)
        self._set_status(text)
        return text

    def unregister_time_series(self, series_id: str) -> None:
        if series_id not in self._time_series:
            raise ValueError(f"Unknown time series ID: {series_id!r}")
        was_source = series_id == self._collapse_source_id
        if was_source:
            self.restore_time_chart()
        del self._time_series[series_id]
        self._plot_dates_by_id.pop(series_id, None)
        self._time_series_sorted.pop(series_id, None)
        self._stream_cadences.pop(series_id, None)
        if was_source:
            self._collapse_source_id = None
        self._sync_context_menu_state()

    def restore_time_chart(self) -> None:
        for registration in self._time_series.values():
            registration.series.restore_source_dates()
        source_dates = None
        if self._collapse_source_id in self._time_series:
            source_dates = np.asarray(
                self._time_series[self._collapse_source_id].series.source_dates,
                dtype=float,
            )
        self._gap_manager.reset(source_dates)
        if (
            self._collapse_source_id is not None
            and self._collapse_source_id in self._stream_cadences
        ):
            self._gap_manager.stream_source_id = self._collapse_source_id
            self._gap_manager.stream_interval = self._stream_cadences[self._collapse_source_id]
        self._plot_dates_by_id = {
            series_id: np.asarray(registration.series.source_dates, dtype=float).copy()
            for series_id, registration in self._time_series.items()
        }
        candle_registration = self._time_series.get("candles")
        if candle_registration is not None:
            self.dates = np.asarray(candle_registration.series.source_dates, dtype=float).copy()
        self._refresh_registered_tools()
        if self._last_axis_resize_info is not None:
            self.axes_resize_callback(None, None, [self._last_axis_resize_info])
        self.context.viewport.wake(full_refresh=True)
        self._sync_context_menu_state()

    @staticmethod
    def _format_spec_to_dict(spec) -> dict[str, object]:
        return {
            "date_fmt": int(spec.date_fmt),
            "time_fmt": int(spec.time_fmt),
            "use_24_hour": bool(spec.use_24_hour),
            "use_iso8601": bool(spec.use_iso8601),
        }

    def _get_unit_for_range(self, span_seconds: float) -> int:
        cutoffs = self.time_unit_range_cutoffs
        for i in range(min(len(cutoffs), locator_time3.TIME_COUNT)):
            if span_seconds <= cutoffs[i]:
                return i
        return locator_time3.TIME_YR

    _UNIT_NAMES: tuple[str, ...] = ("US", "MS", "S", "MIN", "HR", "DAY", "MO", "YR")

    def get_last_resize_time_format_info(self) -> dict[str, object]:
        return dict(self._last_resize_time_format_info)

    @property
    def inject_boundary_ticks(self) -> bool:
        """Compatibility alias for date-context label repair."""
        return self._apply_date_context_labels

    @inject_boundary_ticks.setter
    def inject_boundary_ticks(self, value: bool) -> None:
        self.apply_date_context_labels = value

    @property
    def apply_date_context_labels(self) -> bool:
        """Whether sparse date context should be added to existing x labels."""
        return self._apply_date_context_labels

    @apply_date_context_labels.setter
    def apply_date_context_labels(self, value: bool) -> None:
        self._apply_date_context_labels = bool(value)
        self.X1.fit()
        self._sync_context_menu_state()

    @property
    def label_overlap_debug(self) -> bool:
        """Whether the label-overlap diagnostic overlay is enabled."""
        return self._label_overlap_debug

    @label_overlap_debug.setter
    def label_overlap_debug(self, value: bool) -> None:
        value = bool(value)
        if value == self._label_overlap_debug:
            return
        self._label_overlap_debug = value
        if value:
            self._ensure_diag_series()
        if self._diag_extents_series is not None:
            self._diag_extents_series.show = value
        if self._diag_overlaps_series is not None:
            self._diag_overlaps_series.show = value
        # Trigger a resize callback so diagnostic data is computed immediately
        self.X1.fit()
        self._sync_context_menu_state()

    @property
    def boundary_tick_debug(self) -> bool:
        """Compatibility alias for the date-context diagnostic overlay."""
        return self._date_context_debug

    @boundary_tick_debug.setter
    def boundary_tick_debug(self, value: bool) -> None:
        self.date_context_debug = value

    @property
    def date_context_debug(self) -> bool:
        """Whether the date-context label diagnostic overlay is enabled."""
        return self._date_context_debug

    @date_context_debug.setter
    def date_context_debug(self, value: bool) -> None:
        value = bool(value)
        if value == self._date_context_debug:
            return
        self._date_context_debug = value
        if value:
            self._ensure_diag_series()
        if self._diag_date_context_series is not None:
            self._diag_date_context_series.show = value
        self.X1.fit()
        self._sync_context_menu_state()

    def _format_debug_text(self) -> str:
        """Build a compact multiline debug string from the last resize info and tick counts."""
        info = self._last_resize_time_format_info
        if not info:
            return ""
        u0 = int(info.get("unit0", -1))
        u1 = int(info.get("unit1", -1))
        u0_name = self._UNIT_NAMES[u0] if 0 <= u0 < len(self._UNIT_NAMES) else str(u0)
        u1_name = self._UNIT_NAMES[u1] if 0 <= u1 < len(self._UNIT_NAMES) else str(u1)
        fmt0 = info.get("fmt0", {})
        fmt1 = info.get("fmt1", {})
        fmtf = info.get("fmtf", {})
        tc = self._last_tick_counts
        lines = [
            f"unit0={u0_name}  unit1={u1_name}  collapsed={info.get('collapsed', False)}",
            f"span={info.get('span_seconds', 0):.1f}s  px={info.get('pixels', 0):.0f}  span/100px={info.get('span_per_100px', 0):.2f}",
            f"fmt0: date={fmt0.get('date_fmt')} time={fmt0.get('time_fmt')}",
            f"fmt1: date={fmt1.get('date_fmt')} time={fmt1.get('time_fmt')}",
            f"fmtf: date={fmtf.get('date_fmt')} time={fmtf.get('time_fmt')}",
            f"ticks: L0={tc.get('level0', 0)} L1={tc.get('level1', 0)} total={tc.get('total', 0)}",
            f"labels_rendered={tc.get('labels_rendered', 0)}",
        ]
        if tc.get("date_context_labels", 0) > 0:
            lines.append(f"date_context_labels={tc['date_context_labels']}")
        if tc.get("overlap_count", 0) > 0:
            lines.append(
                f"overlaps: {tc['overlap_count']}  total_width={tc.get('overlap_total_width', 0):.2f}"
            )
        return "\n".join(lines)

    def _compute_label_extents(
        self,
        labels: list[str],
        coords: list[float],
        is_major_flags: list[bool],
        scaling_factor: float,
    ) -> list[tuple[float, float, bool]]:
        """Return (x_start, x_end, is_major) for each label using text-width measurement."""
        measure = getattr(self._time_locator, "measure_text_width_px", None)
        char_px = self._time_locator_char_px
        extents: list[tuple[float, float, bool]] = []
        for label, coord, is_major in zip(labels, coords, is_major_flags):
            if measure is not None:
                width_px = measure(label)
            else:
                width_px = len(label) * char_px
            half_w = (width_px * scaling_factor) / 2.0
            extents.append((coord - half_w, coord + half_w, is_major))
        return extents

    @staticmethod
    def _detect_label_overlaps(
        extents: list[tuple[float, float, bool]],
    ) -> list[tuple[float, float, int, int]]:
        """Scan sorted extents for adjacent overlaps.

        Returns (overlap_start, overlap_end, index_a, index_b) for each collision.
        """
        sorted_entries = sorted(
            [(i, xs, xe) for i, (xs, xe, _) in enumerate(extents)],
            key=lambda t: t[1],
        )
        overlaps: list[tuple[float, float, int, int]] = []
        for k in range(len(sorted_entries) - 1):
            i, _, xe_a = sorted_entries[k]
            j, xs_b, xe_b = sorted_entries[k + 1]
            if xe_a > xs_b:
                overlaps.append((xs_b, min(xe_a, xe_b), i, j))
        return overlaps

    def _ensure_diag_series(self) -> None:
        """Lazily create the diagnostic PlotDigital series and configure Y2."""
        if (
            self._diag_extents_series is not None
            and self._diag_overlaps_series is not None
            and self._diag_date_context_series is not None
        ):
            return
        # Configure Y2 as a fixed 0-1 axis with no visible chrome
        self.Y2.constraint_min = 0.0
        self.Y2.constraint_max = 1.0
        self.Y2.lock_min = True
        self.Y2.lock_max = True
        self.Y2.no_tick_labels = True
        self.Y2.no_tick_marks = True
        self.Y2.no_gridlines = True
        self.Y2.no_label = True
        self.Y2.no_side_switch = True
        self.Y2.no_highlight = True
        self.Y2.no_menus = True
        self.Y2.enabled = True

        y2_axes = (dcg.Axis.X1, dcg.Axis.Y2)
        empty_x = np.array([], dtype=np.float64)
        empty_y = np.array([], dtype=np.float64)
        with self:
            if self._diag_extents_series is None:
                self._diag_extents_series = dcg.PlotDigital(
                    self.context,
                    X=empty_x,
                    Y=empty_y,
                    label="##diag_extents",
                    axes=y2_axes,
                    no_legend=True,
                    theme=dcg.ThemeColorImPlot(self.context, fill=(100, 255, 180, 80)),
                )
            if self._diag_overlaps_series is None:
                self._diag_overlaps_series = dcg.PlotDigital(
                    self.context,
                    X=empty_x,
                    Y=empty_y,
                    label="##diag_overlaps",
                    axes=y2_axes,
                    no_legend=True,
                    theme=dcg.ThemeColorImPlot(self.context, fill=(255, 60, 60, 160)),
                )
            if self._diag_date_context_series is None:
                self._diag_date_context_series = dcg.PlotDigital(
                    self.context,
                    X=empty_x,
                    Y=empty_y,
                    label="##diag_date_context_labels",
                    axes=y2_axes,
                    no_legend=True,
                    theme=dcg.ThemeColorImPlot(self.context, fill=(255, 190, 40, 180)),
                )

        self._diag_extents_series.show = self._label_overlap_debug
        self._diag_overlaps_series.show = self._label_overlap_debug
        self._diag_date_context_series.show = self._date_context_debug

    def get_time_format_config(self) -> dict[str, object]:
        return {
            "unit_range_cutoffs": tuple(self.time_unit_range_cutoffs),
            "level0": [self._format_spec_to_dict(spec) for spec in self.time_format_level0],
            "level1": [self._format_spec_to_dict(spec) for spec in self.time_format_level1],
            "level1_first": [self._format_spec_to_dict(spec) for spec in self.time_format_level1_first],
        }

    def _apply_custom_x_labels(self, labels, coords, *, majors=None, no_gridlines=False) -> None:
        self.X1.keep_default_ticks = False
        self.X1.labels = labels
        self.X1.labels_coord = coords
        if majors is not None:
            self.X1.labels_major = majors
        self.X1.no_gridlines = no_gridlines

    def set_data(
        self,
        *,
        dates,
        opens,
        highs,
        lows,
        closes,
        index=None,
        volume=None,
        volume_kwargs: dict | None = None,
        candle_label: str = "Stock Price",
        candle_weight: float = 0.1,
        time_formatter=None,
        candle_y_axis: dcg.Axis = dcg.Axis.Y1,
    ) -> None:
        old_present = self.candlestick_plot is not None
        old_candle_state = None
        if old_present:
            old_candle_state = {
                "dates": np.asarray(self.candlestick_plot.dates, dtype=float).copy(),
                "source_dates": np.asarray(self.candlestick_plot.source_dates, dtype=float).copy(),
                "opens": np.asarray(self.candlestick_plot.opens, dtype=float).copy(),
                "highs": np.asarray(self.candlestick_plot.highs, dtype=float).copy(),
                "lows": np.asarray(self.candlestick_plot.lows, dtype=float).copy(),
                "closes": np.asarray(self.candlestick_plot.closes, dtype=float).copy(),
                "volumes": np.asarray(self.candlestick_plot.volumes, dtype=float).copy(),
                "y_axis": getattr(self.candlestick_plot, "y_axis", dcg.Axis.Y1),
                "index": np.asarray(self.index).copy(),
                "index_is_default": bool(self._index_is_default),
            }

        new_dates = np.asarray(dates, dtype=float)
        new_opens = np.asarray(opens, dtype=float)
        new_highs = np.asarray(highs, dtype=float)
        new_lows = np.asarray(lows, dtype=float)
        new_closes = np.asarray(closes, dtype=float)
        new_volume = np.zeros_like(new_dates, dtype=float) if volume is None else np.asarray(volume, dtype=float)
        prepared_indicator_states = None
        if self._indicator_manager.indicator_ids:
            prepared = {
                "dates": new_dates.copy(),
                "source_dates": new_dates.copy(),
                "opens": new_opens.copy(),
                "highs": new_highs.copy(),
                "lows": new_lows.copy(),
                "closes": new_closes.copy(),
                "volumes": new_volume.copy(),
            }
            prepared_indicator_states = self._indicator_manager.prepare_candle_state(prepared)

        if self._gap_manager.time_is_collapsed:
            self.restore_time_chart()
        self._stream_cadences.clear()
        self.dates = new_dates
        self.opens = new_opens
        self.highs = new_highs
        self.lows = new_lows
        self.closes = new_closes
        self.index = np.asarray(index) if index is not None else np.arange(self.dates.shape[0])
        self._index_is_default = index is None
        self.volume = new_volume

        if time_formatter is None:
            time_formatter = "auto"

        try:
            if self.candlestick_plot is None:
                with self:
                    self.candlestick_plot = PlotCandleStick(
                        self.context,
                        dates=self.dates,
                        source_dates=self.dates,
                        opens=self.opens,
                        closes=self.closes,
                        lows=self.lows,
                        highs=self.highs,
                        volumes=self.volume,
                        volume_kwargs=(volume_kwargs or {}),
                        label=candle_label,
                        weight=candle_weight,
                        time_formatter=time_formatter,
                        y_axis=candle_y_axis,
                    )
            else:
                self.candlestick_plot.y_axis = candle_y_axis
                self.candlestick_plot.update_all(
                    dates=self.dates,
                    source_dates=self.dates,
                    opens=self.opens,
                    closes=self.closes,
                    lows=self.lows,
                    highs=self.highs,
                    volumes=self.volume,
                )
            if prepared_indicator_states is not None:
                prepared = {
                    "dates": new_dates.copy(),
                    "source_dates": new_dates.copy(),
                    "opens": new_opens.copy(),
                    "highs": new_highs.copy(),
                    "lows": new_lows.copy(),
                    "closes": new_closes.copy(),
                    "volumes": new_volume.copy(),
                }
                self._indicator_manager.publish_candle_state(
                    prepared,
                    prepared_results=prepared_indicator_states,
                )
        except Exception as original_error:
            rollback_errors = []
            if old_present and old_candle_state is not None:
                try:
                    self.dates = old_candle_state["dates"]
                    self.opens = old_candle_state["opens"]
                    self.highs = old_candle_state["highs"]
                    self.lows = old_candle_state["lows"]
                    self.closes = old_candle_state["closes"]
                    self.volume = old_candle_state["volumes"]
                    self.index = old_candle_state["index"]
                    self._index_is_default = old_candle_state["index_is_default"]
                    self.candlestick_plot.y_axis = old_candle_state["y_axis"]
                    self.candlestick_plot.update_all(
                        dates=old_candle_state["dates"],
                        source_dates=old_candle_state["source_dates"],
                        opens=old_candle_state["opens"],
                        closes=old_candle_state["closes"],
                        lows=old_candle_state["lows"],
                        highs=old_candle_state["highs"],
                        volumes=old_candle_state["volumes"],
                    )
                    self._indicator_manager.publish_candle_state(old_candle_state)
                    self._gap_manager.reset(old_candle_state["source_dates"])
                except Exception as exc:
                    rollback_errors.append(exc)
            if rollback_errors:
                raise RuntimeError(
                    "Candle replacement failed and rollback also failed: "
                    + "; ".join(str(error) for error in rollback_errors)
                ) from original_error
            raise

        candle_adapter = _CandleSeriesAdapter(self.candlestick_plot, self)
        self.register_time_series(
            "candles",
            candle_adapter,
            replace="candles" in self._time_series,
            mutation_adapter=candle_adapter,
        )
        if self._collapse_source_id is None:
            self._collapse_source_id = "candles"
        self._gap_manager.reset(self.dates)
        self._refresh_registered_tools()
        self._sync_context_menu_state()

        self._apply_custom_x_labels(
            [str(i) for i in self.index],
            self.dates,
            no_gridlines=[False] * len(self.index),
        )

    def add_gaps_chunks_GUI(self, sender=None, app_data=None, user_data=None) -> None:
        if self._collapse_source_id is None:
            self._set_status("Select a collapse source before inspecting gaps.")
            return
        source_dates = self._time_series[self._collapse_source_id].series.source_dates
        report = self._gap_manager.build_gaps_report(np.asarray(source_dates, dtype=float))
        if not report.gaps:
            self._set_status("No gaps or chunks found.")
            return
        print(report.gaps)
        self._set_status(report.text)

    def collapse_time_chart(self, sender=None, app_data=None, user_data=None, *, debug: bool = True) -> None:
        self._collapse_registered_series(debug=debug, vectorized=False)

    def _collapse_registered_series(self, *, debug: bool, vectorized: bool) -> None:
        if self._gap_manager.time_is_collapsed:
            self._set_status("Time is already collapsed. Reload data to collapse again.")
            self._sync_context_menu_state()
            return
        if self._collapse_source_id is None:
            self._set_status("Select a collapse source before collapsing time.")
            self._sync_context_menu_state()
            return

        start_time = time.time()
        source = self._time_series[self._collapse_source_id]
        source_dates = np.asarray(source.series.source_dates, dtype=float)
        collapse_method = (
            self._gap_manager.collapse_dates_vectorized
            if vectorized
            else self._gap_manager.collapse_dates
        )
        base_step = self._stream_cadences.get(self._collapse_source_id)
        try:
            collapse_method(
                source_dates,
                use_local_time=self._time_locator_use_local_time,
                debug=debug,
                base_step=base_step,
            )
        except Exception as exc:
            self.restore_time_chart()
            self._set_status(f"Time collapse failed: {exc}")
            self._sync_context_menu_state()
            raise
        if self._gap_manager.time_map is None:
            self.restore_time_chart()
            self._set_status("Could not build a time-collapse map from the selected source.")
            self._sync_context_menu_state()
            return

        projections = {
            series_id: self._gap_manager.time_map.project_many(
                np.asarray(registration.series.source_dates, dtype=float),
                in_gap=registration.in_gap,
            )
            for series_id, registration in self._time_series.items()
        }
        try:
            for series_id, dates in projections.items():
                self._time_series[series_id].series.set_plot_dates(dates)
                self._plot_dates_by_id[series_id] = np.asarray(dates, dtype=float).copy()
            self._refresh_registered_tools()
            if self._last_axis_resize_info is not None:
                self.axes_resize_callback(None, None, [self._last_axis_resize_info])
        except Exception:
            self.restore_time_chart()
            raise

        if "candles" in projections:
            self.dates = projections["candles"].copy()

        elapsed = time.time() - start_time
        status_msg = f"Time collapse took {elapsed:.4f} seconds."
        if debug and self._gap_manager.time_map is not None:
            dump_text = self._gap_manager.time_map.debug_dump(limit=16)
            status_msg = f"{status_msg}\n\n{dump_text}"
        self._set_status(status_msg)
        self.context.viewport.wake(full_refresh=True)
        self._sync_context_menu_state()

    def collapse_time_chart_vec(self, sender=None, app_data=None, user_data=None, *, debug: bool = True) -> None:
        self._collapse_registered_series(debug=debug, vectorized=True)

    def load_horizontal_bars(
        self,
        sender=None,
        app_data=None,
        user_data=None,
        *,
        num_bars: int = 200,
        x_min: float = 0.5 * 100000,
        x_max: float = 3.0 * 100000,
        value_space: str = "data",
        normalized_max_fraction: float = 0.35,
    ) -> None:
        if not hasattr(dcg, "PlotColorBars"):
            raise RuntimeError(
                "Horizontal bar rendering requires a DearCyGui build that "
                "provides dcg.PlotColorBars"
            )
        if value_space not in ("data", "normalized"):
            raise ValueError("value_space must be 'data' or 'normalized'")

        if len(self.lows) > 0 and len(self.highs) > 0:
            y_min = float(np.min(self.lows))
            y_max = float(np.max(self.highs))
        else:
            y_min = 0.0
            y_max = 100.0

        X, Y = _generate_sample_bar_data(
            num_bars=num_bars,
            y_min=y_min,
            y_max=y_max,
            x_min=x_min,
            x_max=x_max,
        )
        if value_space == "normalized" and len(X):
            X = np.maximum(np.asarray(X, dtype=float), 0.0)
            maximum = float(np.max(X))
            X = X / maximum if maximum > 0.0 else np.zeros_like(X)

        if self.horizontal_bars is None:
            with self:
                self.horizontal_bars = dcg.PlotColorBars(
                    self.context,
                    X=X,
                    Y=Y,
                    colors=(180, 0, 220, 120),
                    label="Horizontal Bars",
                    horizontal=True,
                    anchor="axis_max",
                    value_space=value_space,
                    normalized_max_fraction=normalized_max_fraction,
                    weight=_horizontal_bar_weight(Y),
                    ignore_fit=True,
                    axes=(dcg.Axis.X1, dcg.Axis.Y1),
                )
            self._set_status(f"Loaded {num_bars} horizontal bars")
        else:
            self.horizontal_bars.X = []
            self.horizontal_bars.Y = []
            self.horizontal_bars.value_space = value_space
            self.horizontal_bars.normalized_max_fraction = normalized_max_fraction
            self.horizontal_bars.weight = _horizontal_bar_weight(Y)
            self.horizontal_bars.X = X
            self.horizontal_bars.Y = Y
            self._set_status(f"Updated {num_bars} horizontal bars")

    def _date_context_spec_for_unit(self, unit0: int):
        if unit0 <= locator_time3.TIME_HR:
            return locator_time3.DateTimeSpec(locator_time3.DATE_DAY_MO, locator_time3.TIMEFMT_NONE)
        if unit0 == locator_time3.TIME_DAY:
            return locator_time3.DateTimeSpec(locator_time3.DATE_MO_YR, locator_time3.TIMEFMT_NONE)
        if unit0 == locator_time3.TIME_MO:
            return locator_time3.DateTimeSpec(locator_time3.DATE_YR, locator_time3.TIMEFMT_NONE)
        return None

    def _expand_x_axis_time(self, x: float) -> float:
        time_map = self._gap_manager.time_map
        if self._gap_manager.time_is_collapsed and time_map is not None:
            return time_map._expand_for_axis(x)
        return x

    def _format_date_context_label(
        self,
        x: float,
        spec,
        *,
        use_local_time: bool,
        use_24_hour: bool,
        use_iso8601: bool,
    ) -> str:
        t_real = self._expand_x_axis_time(x)
        return locator_time3.format_datetime(
            locator_time3.ImPlotTime.from_double(t_real),
            spec,
            use_local_time=use_local_time,
            use_24_hour=use_24_hour,
            use_iso8601=use_iso8601,
        )

    def _apply_date_context_label_repair(
        self,
        by_pos: dict[int, dict[str, object]],
        *,
        min_time: float,
        max_time: float,
        scaling_factor: float | None,
        unit0: int,
        use_local_time: bool,
        use_24_hour: bool,
        use_iso8601: bool,
    ) -> list[float]:
        """Add sparse date context to already-rendered x-label positions."""
        if not by_pos or scaling_factor is None or scaling_factor <= 0:
            return []

        spec = self._date_context_spec_for_unit(unit0)
        if spec is None:
            return []

        entries = sorted(by_pos.values(), key=lambda entry: float(entry["pos"]))
        candidate_entries = [
            entry for entry in entries
            if entry.get("major") is None and entry.get("minor") is not None
        ]
        if not candidate_entries:
            return []

        max_gap = max(float(self.date_context_max_gap_px) * scaling_factor, 1.0)
        min_spacing = max(float(self.date_context_min_spacing_px) * scaling_factor, 0.0)
        major_positions = [float(entry["pos"]) for entry in entries if entry.get("major") is not None]
        anchors = [float(min_time), *major_positions, float(max_time)]
        anchors = sorted(dict.fromkeys(int(round(pos)) for pos in anchors))

        repaired_positions: list[float] = []
        used_keys: set[int] = set()

        for left_key, right_key in zip(anchors, anchors[1:]):
            left = float(left_key)
            right = float(right_key)
            gap = right - left
            if gap <= max_gap:
                continue

            repair_count = max(1, int(gap // max_gap))
            for i in range(repair_count):
                target = left + gap * float(i + 1) / float(repair_count + 1)
                choices = [
                    entry for entry in candidate_entries
                    if left < float(entry["pos"]) < right
                    and int(round(float(entry["pos"]))) not in used_keys
                    and all(abs(float(entry["pos"]) - pos) >= min_spacing for pos in repaired_positions)
                    and all(abs(float(entry["pos"]) - pos) >= min_spacing for pos in major_positions)
                ]
                if not choices:
                    continue

                chosen = min(choices, key=lambda entry: abs(float(entry["pos"]) - target))
                pos = float(chosen["pos"])
                chosen["major"] = self._format_date_context_label(
                    pos,
                    spec,
                    use_local_time=use_local_time,
                    use_24_hour=use_24_hour,
                    use_iso8601=use_iso8601,
                )
                used_keys.add(int(round(pos)))
                repaired_positions.append(pos)

        return repaired_positions

    def axes_resize_callback(self, sender, target, data) -> None:
        x_axis_info = data[0]
        min_time = float(x_axis_info[0])
        max_time = float(x_axis_info[1])
        scaling_factor = float(x_axis_info[2]) if len(x_axis_info) >= 3 else None
        self._last_axis_resize_info = (min_time, max_time)
        if scaling_factor is not None:
            self._last_axis_resize_info += (scaling_factor,)

        span = abs(max_time - min_time)
        if scaling_factor is not None and np.isfinite(scaling_factor) and scaling_factor > 0:
            pixels = span / scaling_factor
        else:
            pixels = 800.0
        if not np.isfinite(pixels) or pixels <= 0:
            pixels = 800.0

        span_per_100px = span / (pixels / 100.0) if pixels > 0 else span
        unit0 = self._get_unit_for_range(span_per_100px)
        unit1 = min(unit0 + 1, locator_time3.TIME_COUNT - 1)
        fmt0 = self.time_format_level0[unit0]
        fmt1 = self.time_format_level1[unit1]
        fmtf = self.time_format_level1_first[unit1]

        self._last_resize_time_format_info = {
            "min_time": min_time,
            "max_time": max_time,
            "span_seconds": span,
            "pixels": pixels,
            "span_per_100px": span_per_100px,
            "unit0": int(unit0),
            "unit1": int(unit1),
            "fmt0": self._format_spec_to_dict(fmt0),
            "fmt1": self._format_spec_to_dict(fmt1),
            "fmtf": self._format_spec_to_dict(fmtf),
            "collapsed": bool(self._gap_manager.time_is_collapsed and self._gap_manager.time_map is not None),
        }

        ticks = self._time_locator(min_time, max_time, pixels)

        date_context_positions: list[float] = []
        use_local_time = bool(getattr(self._time_locator, "use_local_time", True))
        use_24_hour = bool(getattr(self._time_locator, "use_24_hour", False))
        use_iso8601 = bool(getattr(self._time_locator, "use_iso8601", False))

        if self._gap_manager.time_is_collapsed and self._gap_manager.time_map is not None:
            relabeled: list[locator_time3.Tick] = []
            last_major_label: str | None = None
            # Reformat each generated tick from collapsed coordinates back to real-time labels.
            # Level-0 ticks are minor labels; level-1 ticks are major labels with de-dup logic.
            for tk in sorted(ticks, key=lambda t: float(t.pos)):
                pos = float(tk.pos)
                tp = locator_time3.ImPlotTime.from_double(self._expand_x_axis_time(pos))

                if tk.level == 0:
                    label = locator_time3.format_datetime(
                        tp,
                        fmt0,
                        use_local_time=use_local_time,
                        use_24_hour=use_24_hour,
                        use_iso8601=use_iso8601,
                    )
                    relabeled.append(
                        locator_time3.Tick(
                            pos=float(tk.pos),
                            level=0,
                            major=bool(tk.major),
                            show_label=bool(tk.show_label),
                            label=(label if tk.show_label else None),
                        )
                    )
                else:
                    spec = fmtf if last_major_label is None else fmt1
                    label = locator_time3.format_datetime(
                        tp,
                        spec,
                        use_local_time=use_local_time,
                        use_24_hour=use_24_hour,
                        use_iso8601=use_iso8601,
                    )
                    show1 = bool(tk.show_label)
                    if (
                        show1
                        and last_major_label is not None
                        and locator_time3.time_label_same_suffix(last_major_label, label)
                    ):
                        show1 = False
                    relabeled.append(
                        locator_time3.Tick(
                            pos=float(tk.pos),
                            level=1,
                            major=bool(tk.major),
                            show_label=show1,
                            label=(label if show1 else None),
                        )
                    )
                    if show1:
                        last_major_label = label

            ticks = relabeled

        # Group labels by (rounded) x-position so overlapping major/minor ticks can be
        # merged into a single rendered label entry at that coordinate.
        by_pos: dict[int, dict[str, object]] = {}
        # Build major/minor buckets per position from the locator output.
        for t in ticks:
            if not t.show_label or t.label is None:
                continue
            key = int(round(float(t.pos)))
            entry = by_pos.get(key)
            if entry is None:
                entry = {"pos": float(t.pos), "major": None, "minor": None}
                by_pos[key] = entry
            # Old code:
            # is_major = bool(getattr(t, "major", False) or getattr(t, "level", 0) == 1)
            # Use tick level, not tick.major, to choose the label row.
            # In DearCyFi, level-1 is the upper major row and level-0 is the
            # lower minor row. A boundary tick can still be major=True while
            # living on level-0, so tick.major alone is not enough to pick the
            # rendered row.
            is_major = bool(getattr(t, "level", 0) == 1)
            if is_major:
                entry["major"] = t.label
            else:
                entry["minor"] = t.label

        if self._apply_date_context_labels:
            date_context_positions = self._apply_date_context_label_repair(
                by_pos,
                min_time=min_time,
                max_time=max_time,
                scaling_factor=scaling_factor,
                unit0=unit0,
                use_local_time=use_local_time,
                use_24_hour=use_24_hour,
                use_iso8601=use_iso8601,
            )

        labels = []
        coords = []
        majors = []
        # Convert grouped per-position labels into the final axis arrays.
        # A single x-position may carry both rows: upper major row first, then
        # lower minor row on the next line.
        for key in sorted(by_pos, key=lambda k: float(by_pos[k]["pos"])):
            entry = by_pos[key]
            major_label = entry["major"]
            minor_label = entry["minor"]
            if major_label is not None and minor_label is not None:
                if str(major_label) == str(minor_label):
                    label = f"{major_label}"
                else:
                    label = f"{major_label}\n{minor_label}"
            elif major_label is not None:
                label = f"{major_label}"
            elif minor_label is not None:
                label = f"{minor_label}"
            else:
                continue

            labels.append(label)
            coords.append(float(entry["pos"]))
            majors.append(bool(major_label is not None))

        self._apply_custom_x_labels(labels, coords, majors=majors, no_gridlines=False)

        # --- Label overlap diagnostic overlay ---
        overlap_count = 0
        overlap_total_width = 0.0
        if self._label_overlap_debug and scaling_factor is not None and scaling_factor > 0:
            self._ensure_diag_series()
            extents = self._compute_label_extents(labels, coords, majors, scaling_factor)
            overlaps = self._detect_label_overlaps(extents)
            overlap_count = len(overlaps)
            overlap_total_width = sum(oe - os for os, oe, _, _ in overlaps)

            # Build extents step-function arrays for all labels
            ext_x_parts: list[float] = []
            ext_y_parts: list[float] = []
            for xs, xe, _is_major in extents:
                ext_x_parts.extend([xs, xe])
                ext_y_parts.extend([1.0, 0.0])

            self._diag_extents_series.X = np.array(ext_x_parts, dtype=np.float64)
            self._diag_extents_series.Y = np.array(ext_y_parts, dtype=np.float64)

            # Build overlaps step-function arrays
            ovl_x_parts: list[float] = []
            ovl_y_parts: list[float] = []
            for os, oe, _, _ in overlaps:
                ovl_x_parts.extend([os, oe])
                ovl_y_parts.extend([1.0, 0.0])

            self._diag_overlaps_series.X = np.array(ovl_x_parts, dtype=np.float64)
            self._diag_overlaps_series.Y = np.array(ovl_y_parts, dtype=np.float64)

        if self._date_context_debug and scaling_factor is not None and scaling_factor > 0:
            self._ensure_diag_series()
            pulse_half_width = scaling_factor * 2.0
            tick_x_parts: list[float] = []
            tick_y_parts: list[float] = []
            for x in date_context_positions:
                tick_x_parts.extend([x - pulse_half_width, x + pulse_half_width])
                tick_y_parts.extend([0.65, 0.0])

            self._diag_date_context_series.X = np.array(tick_x_parts, dtype=np.float64)
            self._diag_date_context_series.Y = np.array(tick_y_parts, dtype=np.float64)

        # Update tick counts for debug overlay
        n_l0 = sum(1 for t in ticks if t.level == 0)
        n_l1 = sum(1 for t in ticks if t.level == 1)
        self._last_tick_counts = {
            "level0": n_l0,
            "level1": n_l1,
            "total": len(ticks),
            "labels_rendered": len(labels),
            "overlap_count": overlap_count,
            "overlap_total_width": overlap_total_width,
            "date_context_labels": len(date_context_positions),
        }
        self.debug_text.value = self._format_debug_text()

