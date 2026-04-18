import time
from datetime import datetime
from pathlib import Path

import dearcygui as dcg
import numpy as np

from .PyTimeLocator import locator_time3
from .DCG_Bar_Utils import PlotHorizontalBars, generate_sample_bar_data
from .DCG_Candle_Utils import PlotCandleStick
from .candle_utils.gap_utils import GapCollapseManager


class DearCyFi(dcg.Plot):
    """Reusable DearCyGui plot subclass with class-owned time-collapse behavior."""

    def __init__(
        self,
        context: dcg.Context,
        *,
        on_status=None,
        use_local_time: bool = True,
        use_24_hour: bool = False,
        use_iso8601: bool = False,
        max_density: float = 0.5,
        char_px: float = 7.0,
        font_path: str | None = None,
        font_size_px: int = 17,
        prewarm: bool = True,
        inject_boundary_ticks: bool = True,
        **plot_kwargs,
    ) -> None:
        super().__init__(context, **plot_kwargs)
        # use the plot kwargs to pass theme and other config from the DearCyFiDemo viewport initialization down to the plot
        # since the plot needs to know the theme for its time locator font loading logic.

        self._on_status = on_status

        print('loaded version with inject boundary ticks')

        self._time_locator_use_local_time = use_local_time
        self._time_locator_use_24_hour = use_24_hour
        self._time_locator_use_iso8601 = use_iso8601
        self._time_locator_max_density = max_density
        self._time_locator_char_px = char_px
        self._time_locator_font_size_px = font_size_px
        self._inject_boundary_ticks = inject_boundary_ticks

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
        self._last_resize_time_format_info: dict[str, object] = {}

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

        self.candlestick_plot = None
        self.horizontal_bars = None

        self.debug_text = dcg.SharedStr(context, value="")
        self._last_tick_counts: dict[str, int] = {}

        self._label_overlap_debug: bool = False
        self._diag_extents_series = None
        self._diag_overlaps_series = None

        self.X1.label = "Date"
        self.X1.scale = dcg.AxisScale.TIME
        self.Y1.label = "Price ($)"

        self.handlers += [
            dcg.AxesResizeHandler(context, callback=self.axes_resize_callback),
        ]

    def _set_status(self, message: str) -> None:
        if callable(self._on_status):
            self._on_status(str(message))

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
        """Whether boundary tick injection at calendar discontinuities is enabled."""
        return self._inject_boundary_ticks

    @inject_boundary_ticks.setter
    def inject_boundary_ticks(self, value: bool) -> None:
        self._inject_boundary_ticks = bool(value)

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
        if tc.get("boundary_year") or tc.get("boundary_month") or tc.get("boundary_day"):
            lines.append(
                f"boundaries: yr={tc.get('boundary_year', 0)} mo={tc.get('boundary_month', 0)} day={tc.get('boundary_day', 0)}"
            )
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
        if self._diag_extents_series is not None:
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
            self._diag_extents_series = dcg.PlotDigital(
                self.context,
                X=empty_x,
                Y=empty_y,
                label="##diag_extents",
                axes=y2_axes,
                no_legend=True,
                theme=dcg.ThemeColorImPlot(self.context, fill=(100, 255, 180, 80)),
            )
            self._diag_overlaps_series = dcg.PlotDigital(
                self.context,
                X=empty_x,
                Y=empty_y,
                label="##diag_overlaps",
                axes=y2_axes,
                no_legend=True,
                theme=dcg.ThemeColorImPlot(self.context, fill=(255, 60, 60, 160)),
            )

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
    ) -> None:
        self.dates = np.asarray(dates)
        self.opens = np.asarray(opens)
        self.highs = np.asarray(highs)
        self.lows = np.asarray(lows)
        self.closes = np.asarray(closes)
        self.index = np.asarray(index) if index is not None else np.arange(self.dates.shape[0])
        if volume is None:
            self.volume = np.zeros_like(self.dates, dtype=float)
        else:
            self.volume = np.asarray(volume)

        self._gap_manager.reset(self.dates)

        if time_formatter is None:
            time_formatter = lambda x: datetime.fromtimestamp(x).strftime("%b %d")

        if self.candlestick_plot is None:
            with self:
                self.candlestick_plot = PlotCandleStick(
                    self.context,
                    dates=self.dates,
                    opens=self.opens,
                    closes=self.closes,
                    lows=self.lows,
                    highs=self.highs,
                    volumes=self.volume,
                    volume_kwargs=(volume_kwargs or {}),
                    label=candle_label,
                    weight=candle_weight,
                    time_formatter=time_formatter,
                )
        else:
            self.candlestick_plot.update_all(
                dates=self.dates,
                opens=self.opens,
                closes=self.closes,
                lows=self.lows,
                highs=self.highs,
                volumes=self.volume,
            )

        self._apply_custom_x_labels(
            [str(i) for i in self.index],
            self.dates,
            no_gridlines=[False] * len(self.index),
        )

    def add_gaps_chunks_GUI(self, sender=None, app_data=None, user_data=None) -> None:
        report = self._gap_manager.build_gaps_report(self.dates)
        if not report.gaps:
            self._set_status("No gaps or chunks found.")
            return
        print(report.gaps)
        self._set_status(report.text)

    def collapse_time_chart(self, sender=None, app_data=None, user_data=None, *, debug: bool = True) -> None:
        if self._gap_manager.time_is_collapsed:
            self._set_status("Time is already collapsed. Reload data to collapse again.")
            return

        start_time = time.time()
        collapsed_dates = self._gap_manager.collapse_dates(
            self.dates,
            use_local_time=self._time_locator_use_local_time,
            debug=debug,
        )

        old_dates = np.array(self.candlestick_plot.dates, copy=True)
        self.candlestick_plot.update(dates=collapsed_dates)
        self.dates = collapsed_dates

        if np.array_equal(old_dates, np.array(self.candlestick_plot.dates)):
            print("Dates did not change after collapsing time.")
        else:
            print("Dates successfully collapsed.")

        elapsed = time.time() - start_time
        status_msg = f"Time collapse took {elapsed:.4f} seconds."
        if debug and self._gap_manager.time_map is not None:
            dump_text = self._gap_manager.time_map.debug_dump(limit=16)
            status_msg = f"{status_msg}\n\n{dump_text}"
        self._set_status(status_msg)

    def collapse_time_chart_vec(self, sender=None, app_data=None, user_data=None, *, debug: bool = True) -> None:
        if self._gap_manager.time_is_collapsed:
            self._set_status("Time is already collapsed. Reload data to collapse again.")
            return

        start_time = time.time()
        collapsed_dates = self._gap_manager.collapse_dates_vectorized(
            self.dates,
            use_local_time=self._time_locator_use_local_time,
            debug=debug,
        )

        old_dates = np.array(self.candlestick_plot.dates, copy=True)
        self.candlestick_plot.update(dates=collapsed_dates)
        self.dates = collapsed_dates

        if np.array_equal(old_dates, np.array(self.candlestick_plot.dates)):
            print("Dates did not change after collapsing time.")
        else:
            print("Dates successfully collapsed.")

        elapsed = time.time() - start_time
        status_msg = f"Time collapse took {elapsed:.4f} seconds."
        if debug and self._gap_manager.time_map is not None:
            dump_text = self._gap_manager.time_map.debug_dump(limit=16)
            status_msg = f"{status_msg}\n\n{dump_text}"
        self._set_status(status_msg)

    def load_horizontal_bars(
        self,
        sender=None,
        app_data=None,
        user_data=None,
        *,
        num_bars: int = 200,
        x_min: float = 0.5 * 100000,
        x_max: float = 3.0 * 100000,
    ) -> None:
        if len(self.lows) > 0 and len(self.highs) > 0:
            y_min = float(np.min(self.lows))
            y_max = float(np.max(self.highs))
        else:
            y_min = 0.0
            y_max = 100.0

        X, Y = generate_sample_bar_data(
            num_bars=num_bars,
            y_min=y_min,
            y_max=y_max,
            x_min=x_min,
            x_max=x_max,
        )

        if self.horizontal_bars is None:
            with self:
                self.horizontal_bars = PlotHorizontalBars(
                    self.context,
                    X=X,
                    Y=Y,
                    axis_x_max=self.X1.max,
                    color=(180, 0, 220, 120),
                    label="Horizontal Bars",
                )
            self._set_status(f"Loaded {num_bars} horizontal bars")
        else:
            self.horizontal_bars.update(X=X, Y=Y)
            self.horizontal_bars.update_positions(self.X1.max)
            self._set_status(f"Updated {num_bars} horizontal bars")

    def _inject_boundary_ticks_at_discontinuities(
        self,
        ticks: list,
        boundaries,
        min_time: float,
        max_time: float,
        span: float,
        use_local_time: bool,
        use_24_hour: bool,
        use_iso8601: bool,
    ) -> dict[str, int]:
        """Inject major ticks at calendar boundaries (year/month/day) within the visible range.

        Maps real timestamps back into collapsed axis coordinates and appends labelled ticks
        to *ticks* in-place.  Returns a dict mapping each boundary kind to the number of
        ticks injected.

        Args:
            ticks: List of Tick objects to append boundary ticks to (modified in-place).
            boundaries: Time-map object exposing year/month/day_starts_real arrays.
            min_time: Lower bound of the visible collapsed axis range.
            max_time: Upper bound of the visible collapsed axis range.
            span: Visible time span in seconds (used to decide whether to include day boundaries).
            use_local_time: Format timestamps in local time when True.
            use_24_hour: Use 24-hour clock format when True.
            use_iso8601: Use ISO 8601 date format when True.
        """
        include_days = (span / 86400.0) <= 60.0
        boundary_arrays: list[tuple[str, np.ndarray]] = [
            ("year", boundaries.year_starts_real),
            ("month", boundaries.month_starts_real),
        ]
        if include_days:
            boundary_arrays.append(("day", boundaries.day_starts_real))

        # Inject additional major ticks at calendar boundaries (year/month/day)
        # using real timestamps, then map them back into collapsed axis coordinates.
        _boundary_counts: dict[str, int] = {}
        for kind, arr in boundary_arrays:
            if arr.size == 0:
                continue
            _kind_count = 0
            for t_real in arr:
                x = float(self._gap_manager.time_map.collapse(float(t_real)))
                if x < min_time or x > max_time:
                    continue
                tp = locator_time3.ImPlotTime.from_double(float(t_real))
                if kind == "year":
                    spec = locator_time3.DateTimeSpec(locator_time3.DATE_YR, locator_time3.TIMEFMT_NONE)
                elif kind == "month":
                    spec = locator_time3.DateTimeSpec(locator_time3.DATE_MO_YR, locator_time3.TIMEFMT_NONE)
                else:
                    # This else statement is suspect for causing excessive tick generation when day boundaries are included.
                    spec = locator_time3.DateTimeSpec(locator_time3.DATE_DAY_MO, locator_time3.TIMEFMT_NONE)
                label = locator_time3.format_datetime(
                    tp,
                    spec,
                    use_local_time=use_local_time,
                    use_24_hour=use_24_hour,
                    use_iso8601=use_iso8601,
                )
                ticks.append(locator_time3.Tick(pos=x, level=1, major=True, show_label=True, label=label))
                _kind_count += 1
            _boundary_counts[kind] = _kind_count
        return _boundary_counts

    def axes_resize_callback(self, sender, target, data) -> None:
        x_axis_info = data[0]
        min_time = float(x_axis_info[0])
        max_time = float(x_axis_info[1])
        scaling_factor = float(x_axis_info[2]) if len(x_axis_info) >= 3 else None

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

        if self._gap_manager.time_is_collapsed and self._gap_manager.time_map is not None:
            use_local_time = bool(getattr(self._time_locator, "use_local_time", True))
            use_24_hour = bool(getattr(self._time_locator, "use_24_hour", False))
            use_iso8601 = bool(getattr(self._time_locator, "use_iso8601", False))

            relabeled: list[locator_time3.Tick] = []
            last_major_label: str | None = None
            # Reformat each generated tick from collapsed coordinates back to real-time labels.
            # Level-0 ticks are minor labels; level-1 ticks are major labels with de-dup logic.
            for tk in sorted(ticks, key=lambda t: float(t.pos)):
                t_real = self._gap_manager.time_map.expand(float(tk.pos))
                tp = locator_time3.ImPlotTime.from_double(float(t_real))

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
                    if show1 and last_major_label is not None and locator_time3.time_label_same_suffix(last_major_label, label):
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

            if self._inject_boundary_ticks:
                _boundary_counts = self._inject_boundary_ticks_at_discontinuities(
                    ticks=ticks,
                    boundaries=self._gap_manager.time_map,
                    min_time=min_time,
                    max_time=max_time,
                    span=span,
                    use_local_time=use_local_time,
                    use_24_hour=use_24_hour,
                    use_iso8601=use_iso8601,
                )
                self._last_tick_counts.update({
                    f"boundary_{k}": v for k, v in _boundary_counts.items()
                })

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
            # New code: use tick level to determine major vs minor, since some locators may not set 'major' flag consistently.
            # Use tick level to choose label lane. Level-1 => major (top line),
            # level-0 => minor (bottom line). This preserves midnight hour ticks
            # when level-0 boundary ticks happen to carry major=True.
            is_major = bool(getattr(t, "level", 0) == 1)
            if is_major:
                entry["major"] = t.label
            else:
                entry["minor"] = t.label

        labels = []
        coords = []
        majors = []
        # Convert grouped per-position labels into final axis arrays expected by DearCyGui.
        # If both major+minor exist at same x, render as two lines; otherwise render whichever exists.
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
        }
        self.debug_text.value = self._format_debug_text()

        if self.horizontal_bars is not None:
            self.horizontal_bars.update_positions(max_time)
