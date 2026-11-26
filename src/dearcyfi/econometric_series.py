import datetime
import math
from collections.abc import Callable, Sized

import dearcygui as dcg
import numpy as np

from ._series_tooltips import _DrawnHoverCondition

_SUPPORTED_Y_AXES = (dcg.Axis.Y1, dcg.Axis.Y2, dcg.Axis.Y3)
_LEGACY_OPTIONS = ("line_kwargs", "marker_kwargs")

DEFAULT_LINE_COLOR = (255, 196, 0, 255)
DEFAULT_LINE_THICKNESS = 1.5
DEFAULT_MARKER_RADIUS = 3.0
TOOLTIP_HIT_SIZE = 8


def _validate_y_axis(y_axis: dcg.Axis) -> dcg.Axis:
    if y_axis not in _SUPPORTED_Y_AXES:
        raise ValueError("y_axis must be dcg.Axis.Y1, dcg.Axis.Y2, or dcg.Axis.Y3")
    return y_axis


def _validate_screen_size(name: str, value: float) -> float:
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a positive finite number of screen pixels")
    return value


class PlotEconometricSeries(dcg.DrawInPlot):
    """Scalar, low-frequency econometric series drawn as one legend item.

    The series is a single legend-enabled ``dcg.DrawInPlot`` whose children are
    the line (``DrawPolyline`` runs between consecutive finite observations),
    optional observation markers (``DrawCircle``) and optional tooltip hit
    regions (``DrawInvisibleButton``). Because every primitive lives under one
    plot item, hiding the series from the legend hides the line, markers and
    hover targets together, and a hidden series does not affect axis fitting.

    Missing observations (NaN values or timestamps) break the line; they are
    never interpolated or forward-filled.

    Args:
        context: DearCyGui context.
        dates: Plotted X coordinates (POSIX seconds).
        values: One numeric value per date.
        label: Legend label and tooltip title.
        source_dates: Original observation timestamps shown in tooltips.
            Defaults to ``dates``.
        markers: Draw a circle at each finite observation.
        tooltip: Show a tooltip when hovering an observation.
        time_formatter: Callable formatting a source timestamp for the tooltip.
        value_formatter: Callable formatting a value for the tooltip.
        y_axis: ``dcg.Axis.Y1``, ``Y2`` or ``Y3``.
        line_color: Line color. Defaults to ``DEFAULT_LINE_COLOR``.
        line_thickness: Line thickness in screen pixels.
        marker_color: Marker color. Defaults to ``line_color``.
        marker_radius: Marker radius in screen pixels; constant while zooming.
        no_legend: Hide the legend entry. Defaults to ``False``.
        **kwargs: Other ``dcg.DrawInPlot`` options such as ``show`` or
            ``ignore_fit``. ``axes`` is rejected; use ``y_axis``.

    Migration from the native ``PlotLine``/``PlotScatter`` implementation:
    the ``line``, ``markers`` and ``_interaction_layer`` attributes and the
    ``line_kwargs``/``marker_kwargs`` options no longer exist. Use
    ``line_color``, ``line_thickness``, ``marker_color`` and ``marker_radius``.
    """

    def __init__(
        self,
        context: dcg.Context,
        *,
        dates: Sized,
        values: Sized,
        label: str = "Econometric Series",
        source_dates: Sized | None = None,
        markers: bool = False,
        tooltip: bool = True,
        time_formatter: Callable[[float], str] | None = None,
        value_formatter: Callable[[float], str] | None = None,
        y_axis: dcg.Axis = dcg.Axis.Y1,
        line_color=DEFAULT_LINE_COLOR,
        line_thickness: float = DEFAULT_LINE_THICKNESS,
        marker_color=None,
        marker_radius: float = DEFAULT_MARKER_RADIUS,
        no_legend: bool = False,
        **kwargs,
    ) -> None:
        for option in _LEGACY_OPTIONS:
            if option in kwargs:
                raise ValueError(
                    f"{option} is no longer supported; use line_color, line_thickness, "
                    "marker_color, and marker_radius instead"
                )
        if "axes" in kwargs:
            raise ValueError("axes cannot be supplied; use y_axis instead")
        y_axis = _validate_y_axis(y_axis)
        line_thickness = _validate_screen_size("line_thickness", line_thickness)
        marker_radius = _validate_screen_size("marker_radius", marker_radius)
        plot_dates, original_dates, numeric_values = self._validated_arrays(
            dates,
            values,
            source_dates,
        )

        super().__init__(context, label=str(label), axes=(dcg.Axis.X1, y_axis), **kwargs)
        # DrawInPlot hides itself from the legend by default.
        self.no_legend = no_legend

        self._y_axis = y_axis
        self._plot_dates = plot_dates
        self._source_dates = original_dates
        self._values = numeric_values
        self._markers = bool(markers)
        self._tooltip = bool(tooltip)
        self._time_formatter = time_formatter or self._default_time_formatter
        self._value_formatter = value_formatter or self._default_value_formatter
        self._line_color = line_color
        self._line_thickness = line_thickness
        self._marker_color = line_color if marker_color is None else marker_color
        self._marker_radius = marker_radius
        self._active_tooltip = None
        self._active_tooltip_target = None
        self._active_tooltip_condition = None
        self.render()

    @staticmethod
    def _validated_arrays(dates, values, source_dates=None):
        plot_dates = np.asarray(dates, dtype=float)
        numeric_values = np.asarray(values, dtype=float)
        original_dates = plot_dates if source_dates is None else np.asarray(source_dates, dtype=float)
        if plot_dates.ndim != 1 or numeric_values.ndim != 1 or original_dates.ndim != 1:
            raise ValueError("dates, source_dates, and values must be one-dimensional")
        if len(plot_dates) != len(numeric_values):
            raise ValueError("dates and values must be the same length")
        if len(original_dates) != len(plot_dates):
            raise ValueError("source_dates must be the same length as dates")
        return plot_dates.copy(), original_dates.copy(), numeric_values.copy()

    @staticmethod
    def _default_time_formatter(timestamp: float) -> str:
        return datetime.datetime.fromtimestamp(float(timestamp)).strftime("%Y-%m-%d")

    @staticmethod
    def _default_value_formatter(value: float) -> str:
        return f"{float(value):,.4g}"

    def _finite_runs(self) -> list[np.ndarray]:
        finite = np.isfinite(self._plot_dates) & np.isfinite(self._values)
        indices = np.flatnonzero(finite)
        if indices.size == 0:
            return []
        return np.split(indices, np.flatnonzero(np.diff(indices) != 1) + 1)

    def render(self) -> None:
        """Rebuild all drawing primitives from the current plot dates and values."""
        self._clear_active_tooltip()
        self.children = [child for child in self.children if isinstance(child, dcg.uiItem)]
        runs = self._finite_runs()
        buttons = []
        with self:
            for run in runs:
                if run.size > 1:
                    dcg.DrawPolyline(
                        self.context,
                        points=[(float(self._plot_dates[i]), float(self._values[i])) for i in run],
                        color=self._line_color,
                        thickness=-self._line_thickness,
                    )
                elif not self._markers:
                    # Invisible anchor so isolated observations still contribute to fitting.
                    dcg.DrawCircle(
                        self.context,
                        center=(float(self._plot_dates[run[0]]), float(self._values[run[0]])),
                        radius=0.0,
                        color=0,
                        fill=0,
                    )
            if self._markers:
                for run in runs:
                    for i in run:
                        dcg.DrawCircle(
                            self.context,
                            center=(float(self._plot_dates[i]), float(self._values[i])),
                            radius=-self._marker_radius,
                            color=self._marker_color,
                            fill=self._marker_color,
                            thickness=-1.0,
                        )
            if self._tooltip:
                for run in runs:
                    for i in run:
                        point = (float(self._plot_dates[i]), float(self._values[i]))
                        buttons.append(
                            dcg.DrawInvisibleButton(
                                self.context,
                                button=0,
                                p1=point,
                                p2=point,
                                min_side=TOOLTIP_HIT_SIZE,
                                user_data=(float(self._source_dates[i]), float(self._values[i])),
                            )
                        )
        if buttons:
            handlers = [
                dcg.GotHoverHandler(self.context, callback=self._tooltip_handler),
                dcg.LostHoverHandler(self.context, callback=self._tooltip_lost_handler),
            ]
            for button in buttons:
                button.handlers = handlers

    def _clear_active_tooltip(self) -> None:
        if self._active_tooltip is not None:
            try:
                self._active_tooltip.delete_item()
            except Exception:
                pass
        target = self._active_tooltip_target
        condition = self._active_tooltip_condition
        if target is not None and condition is not None:
            try:
                target.handlers = [handler for handler in target.handlers if handler is not condition]
            except Exception:
                pass
        self._active_tooltip = None
        self._active_tooltip_target = None
        self._active_tooltip_condition = None

    def _tooltip_handler(self, sender, target) -> None:
        if not self._tooltip:
            return
        if target is self._active_tooltip_target and self._active_tooltip is not None:
            return
        plot = self.parent
        tooltip_parent = plot.parent if plot is not None else None
        if tooltip_parent is None:
            return
        source_date, value = target.user_data
        self._clear_active_tooltip()
        condition = _DrawnHoverCondition(self.context)
        target.handlers = list(target.handlers) + [condition]
        # Parent outside the series so the tooltip is not drawn in its legend popup.
        with dcg.Tooltip(
            self.context,
            target=target,
            condition_from_handler=condition,
            parent=tooltip_parent,
        ) as tooltip:
            dcg.Text(self.context, value=self.label)
            dcg.Text(self.context, value=f"Date: {self._time_formatter(source_date)}")
            dcg.Text(self.context, value=f"Value: {self._value_formatter(value)}")
        self._active_tooltip = tooltip
        self._active_tooltip_target = target
        self._active_tooltip_condition = condition

    def _tooltip_lost_handler(self, sender, target) -> None:
        if target is self._active_tooltip_target:
            self._clear_active_tooltip()

    def update_all(self, *, dates, values, source_dates=None, label: str | None = None) -> None:
        plot_dates, original_dates, numeric_values = self._validated_arrays(
            dates,
            values,
            source_dates,
        )
        self._plot_dates = plot_dates
        self._source_dates = original_dates
        self._values = numeric_values
        if label is not None:
            self.label = str(label)
        self.render()

    def set_plot_dates(self, dates) -> None:
        plot_dates = np.asarray(dates, dtype=float)
        if plot_dates.ndim != 1 or len(plot_dates) != len(self._source_dates):
            raise ValueError("plot dates must be one-dimensional and match source_dates length")
        self._plot_dates = plot_dates.copy()
        self.render()

    def restore_source_dates(self) -> None:
        self.set_plot_dates(self._source_dates)

    @property
    def source_dates(self) -> np.ndarray:
        return self._source_dates.copy()

    @property
    def plot_dates(self) -> np.ndarray:
        return self._plot_dates.copy()

    @property
    def values(self) -> np.ndarray:
        return self._values.copy()

    @property
    def y_axis(self) -> dcg.Axis:
        return self._y_axis
