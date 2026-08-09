import datetime
from collections.abc import Callable, Sized

import dearcygui as dcg
import numpy as np

_SUPPORTED_Y_AXES = (dcg.Axis.Y1, dcg.Axis.Y2, dcg.Axis.Y3)


def _validate_y_axis(y_axis: dcg.Axis) -> dcg.Axis:
    if y_axis not in _SUPPORTED_Y_AXES:
        raise ValueError("y_axis must be dcg.Axis.Y1, dcg.Axis.Y2, or dcg.Axis.Y3")
    return y_axis


class PlotEconometricSeries:
    """Native line series for scalar, low-frequency econometric observations."""

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
        line_kwargs: dict | None = None,
        marker_kwargs: dict | None = None,
    ) -> None:
        self.context = context
        self._label = str(label)
        self._tooltip = bool(tooltip)
        self._time_formatter = time_formatter or self._default_time_formatter
        self._value_formatter = value_formatter or self._default_value_formatter
        self._y_axis = _validate_y_axis(y_axis)
        axes = (dcg.Axis.X1, self._y_axis)

        plot_dates, original_dates, numeric_values = self._validated_arrays(
            dates,
            values,
            source_dates,
        )
        self._plot_dates = plot_dates
        self._source_dates = original_dates
        self._values = numeric_values

        line_options = dict(line_kwargs or {})
        if "axes" in line_options:
            raise ValueError("line_kwargs cannot contain axes; use y_axis instead")
        if marker_kwargs is not None and "axes" in marker_kwargs:
            raise ValueError("marker_kwargs cannot contain axes; use y_axis instead")
        line_options.setdefault("label", self._label)
        line_options.setdefault("skip_nan", False)
        self.line = dcg.PlotLine(
            context,
            X=self._plot_dates,
            Y=self._values,
            axes=axes,
            **line_options,
        )

        self.markers = None
        if markers:
            marker_options = dict(marker_kwargs or {})
            marker_options.setdefault("label", f"{self._label} observations")
            marker_options.setdefault("no_legend", True)
            self.markers = dcg.PlotScatter(
                context,
                X=self._plot_dates,
                Y=self._values,
                axes=axes,
                **marker_options,
            )

        self._interaction_layer = dcg.DrawInPlot(context, axes=axes)
        self._render_interactions()

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

    def _render_interactions(self) -> None:
        self._interaction_layer.children = []
        if not self._tooltip:
            return

        buttons = []
        with self._interaction_layer:
            for plot_date, source_date, value in zip(
                self._plot_dates,
                self._source_dates,
                self._values,
            ):
                if not np.isfinite(plot_date) or not np.isfinite(value):
                    continue
                buttons.append(
                    dcg.DrawInvisibleButton(
                        self.context,
                        button=0,
                        p1=(float(plot_date), float(value)),
                        p2=(float(plot_date), float(value)),
                        min_side=8,
                        user_data=(float(source_date), float(value)),
                    )
                )

        tooltip_handler = dcg.GotHoverHandler(self.context, callback=self._tooltip_handler)
        for button in buttons:
            button.handlers = [tooltip_handler]

    def _tooltip_handler(self, sender, target) -> None:
        source_date, value = target.user_data
        with dcg.utils.TemporaryTooltip(
            self.context,
            target=target,
            parent=target.parent.parent,
        ):
            dcg.Text(self.context, value=self._label)
            dcg.Text(self.context, value=f"Date: {self._time_formatter(source_date)}")
            dcg.Text(self.context, value=f"Value: {self._value_formatter(value)}")

    def update_all(self, *, dates, values, source_dates=None, label: str | None = None) -> None:
        plot_dates, original_dates, numeric_values = self._validated_arrays(
            dates,
            values,
            source_dates,
        )
        new_label = self._label if label is None else str(label)

        self._plot_dates = plot_dates
        self._source_dates = original_dates
        self._values = numeric_values
        self._label = new_label
        self.line.label = new_label
        self.line.X = self._plot_dates
        self.line.Y = self._values
        if self.markers is not None:
            self.markers.label = f"{new_label} observations"
            self.markers.X = self._plot_dates
            self.markers.Y = self._values
        self._render_interactions()

    def set_plot_dates(self, dates) -> None:
        plot_dates = np.asarray(dates, dtype=float)
        if plot_dates.ndim != 1 or len(plot_dates) != len(self._source_dates):
            raise ValueError("plot dates must be one-dimensional and match source_dates length")
        plot_dates = plot_dates.copy()

        self._plot_dates = plot_dates
        self.line.X = self._plot_dates
        if self.markers is not None:
            self.markers.X = self._plot_dates
        self._render_interactions()

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
    def label(self) -> str:
        return self._label

    @property
    def y_axis(self) -> dcg.Axis:
        return self._y_axis