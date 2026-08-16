import datetime
from collections.abc import Callable
import dearcygui as dcg
import numpy as np
from collections.abc import Sized

# Auto tooltip formats are checked from coarsest to finest cadence. The seconds
# values are canonical candle intervals used as tolerant thresholds, not exact
# matches, so irregular market gaps do not usually change the selected format.
_AUTO_TOOLTIP_FORMATS: tuple[tuple[float, str], ...] = (
    (7 * 86400, "%Y-%m-%d"),
    (86400, "%Y-%m-%d"),
    (3600, "%Y-%m-%d %I:%M %p"),
    (15 * 60, "%Y-%m-%d %I:%M %p"),
    (5 * 60, "%Y-%m-%d %I:%M %p"),
    (60, "%Y-%m-%d %I:%M %p"),
)
_AUTO_TOOLTIP_FALLBACK_FORMAT = "%Y-%m-%d %I:%M:%S %p"
_SUPPORTED_Y_AXES = (dcg.Axis.Y1, dcg.Axis.Y2, dcg.Axis.Y3)
_DEFAULT_VOLUME_MAX_FRACTION = 0.20


def _validate_y_axis(y_axis: dcg.Axis) -> dcg.Axis:
    if y_axis not in _SUPPORTED_Y_AXES:
        raise ValueError("y_axis must be dcg.Axis.Y1, dcg.Axis.Y2, or dcg.Axis.Y3")
    return y_axis


def _median_candle_delta_seconds(dates: Sized) -> float | None:
    values = np.asarray(dates, dtype=float)
    values = values[np.isfinite(values)]
    if values.size < 2:
        return None

    deltas = np.diff(np.sort(values))
    deltas = deltas[np.isfinite(deltas) & (deltas > 0)]
    if deltas.size == 0:
        return None
    return float(np.median(deltas))


def _select_auto_tooltip_time_format(dates: Sized) -> str:
    median_delta = _median_candle_delta_seconds(dates)
    if median_delta is None:
        return _AUTO_TOOLTIP_FALLBACK_FORMAT

    for cadence_seconds, format_string in _AUTO_TOOLTIP_FORMATS:
        # Treat each cadence as a range by accepting intervals within 75% of it;
        # larger cadences have already been checked earlier in the table.
        if median_delta >= cadence_seconds * 0.75:
            return format_string
    return _AUTO_TOOLTIP_FALLBACK_FORMAT


def _make_auto_tooltip_time_formatter(dates: Sized):
    format_string = _select_auto_tooltip_time_format(dates)
    return lambda timestamp: datetime.datetime.fromtimestamp(timestamp).strftime(format_string).lower()

class PlotCandleStick(dcg.DrawInPlot):
    """
    Adds a candle series to a plot.

    See the source code for how to make
    a custom version with more interactions.

    Volume Scaling Note:
        Non-negative volume magnitudes are normalized independently of the price
        scale. By default the largest volume occupies 20% of the visible plot
        height and remains bottom-anchored while the selected Y-axis is zoomed.

    Args:
        dates (np.ndarray): x-axis values
        source_dates (np.ndarray, optional): original timestamps used for labels/tooltips
        opens (np.ndarray): open values
        closes (np.ndarray): close values 
        lows (np.ndarray): low values
        highs (np.ndarray): high values
        volumes (np.ndarray, optional): volume values for volume plot
        time_counts (list, optional): Time count annotations for each candle. 
            Each element is a list/array of 0-3 integers to display above/below the candle.
            Example: [[1, 2], [], [3], [1, 2, 3], ...]
        count_position (str, optional): Position of time counts - 'above' (default) or 'below'
        count_offset (float, optional): Vertical spacing multiplier between stacked counts (default 0.5)
        bull_color (color, optional): color of the candlestick when the close is higher than the open
        bear_color (color, optional): color of the candlestick when the close is lower than the open
        weight (float, optional): Candle width as a percentage of the distance between two dates
        tooltip (bool, optional): whether to show a tooltip on hover
        time_formatter (callback | "auto", optional): callback that takes a date and returns a string,
            or "auto" to choose a timestamp format from the median candle interval
    """
    def __init__(self,
                 context : dcg.Context,
                 no_legend=False,
                 dates: Sized = [],
                 source_dates: Sized | None = None,
                 opens: Sized = [],
                 closes: Sized = [],
                 lows: Sized = [],
                 highs: Sized = [],
                 volumes: Sized | None = None,
                 volume_kwargs: dict | None = None,
                 time_counts: list | None = None,
                 count_position: str = 'above',
                 count_offset: float = 0.5,
                 bull_color=(0, 255, 113, 255),
                 bear_color=(218, 13, 79, 255),
                 weight=0.25,
                 tooltip=True,
                 time_formatter=None,
                 y_axis: dcg.Axis = dcg.Axis.Y1,
                 **kwargs) -> None:
        if "axes" in kwargs:
            raise ValueError("axes cannot be supplied with y_axis; use y_axis instead")
        if volume_kwargs is not None and "axes" in volume_kwargs:
            raise ValueError("volume_kwargs cannot contain axes; use y_axis instead")
        self._y_axis = _validate_y_axis(y_axis)
        axes = (dcg.Axis.X1, self._y_axis)
        super().__init__(context, axes=axes, **kwargs)
        # For DrawInPlot, default no_legend is True
        # Thus the override.
        self.no_legend = no_legend
        # normalize volumes default
        if volumes is None:
            volumes = []
        if source_dates is None:
            source_dates = dates
        # normalize time_counts default
        if time_counts is None:
            time_counts = []
        # basic length check (volumes optional)
        if len(dates) != len(opens) or len(dates) != len(closes) \
           or len(dates) != len(lows) or len(dates) != len(highs):
            raise ValueError("dates, opens, closes, lows, highs must be of same length")
        if len(source_dates) != len(dates):
            raise ValueError("source_dates must be the same length as dates")
        # Same to local variables
        self._dates = dates
        self._source_dates = source_dates
        self._opens = opens
        self._closes = closes
        self._lows = lows
        self._highs = highs
        self._volumes = volumes
        self._time_counts = time_counts
        self._count_position = count_position
        self._count_offset = count_offset
        self._bull_color = dcg.color_as_int(bull_color)
        self._bear_color = dcg.color_as_int(bear_color)
        self._weight = float(weight)

        # volume item handling
        if not hasattr(dcg, "PlotColorBars"):
            raise RuntimeError(
                "PlotCandleStick volume rendering requires a DearCyGui build "
                "that provides dcg.PlotColorBars"
            )
        self._volume_bar_series = None
        self._volume_kwargs = dict(volume_kwargs or {})
        self._volume_kwargs["axes"] = axes
        self._volume_kwargs.setdefault("anchor", "axis_min")
        self._volume_kwargs.setdefault("value_space", "normalized")
        self._volume_kwargs.setdefault("normalized_max_fraction", _DEFAULT_VOLUME_MAX_FRACTION)
        self._volume_kwargs.setdefault("ignore_fit", True)
        self._volume_uses_default_weight = "weight" not in self._volume_kwargs
        self._volume_kwargs.setdefault("weight", self._volume_bar_weight())
        self._volume_color_override = self._volume_kwargs.pop("colors", None)
        self._volume_bar_series = dcg.PlotColorBars(context, **self._volume_kwargs)

        self._tooltip = tooltip
        # Tooltip lifecycle state machine:
        # - no active tooltip: (_active_tooltip is None, _active_tooltip_target is None)
        # - active tooltip: one Tooltip instance bound to one hovered candle button
        # On GotHover we reuse if the same target is already active, otherwise
        # replace the previous tooltip. On LostHover we clear the active tooltip.
        # This avoids occasional duplicate OHLC blocks if hover callbacks fire
        # more than once for the same item.
        self._active_tooltip = None
        self._active_tooltip_target = None
        self._update_volume_series()

        self._time_formatter_input = time_formatter
        self._refresh_time_formatter()

        self.render()


    def _refresh_time_formatter(self) -> None:
        if self._time_formatter_input is None:
            self._time_formatter = lambda timestamp: datetime.datetime.fromtimestamp(timestamp).strftime(_AUTO_TOOLTIP_FALLBACK_FORMAT).lower()
        elif isinstance(self._time_formatter_input, str):
            if self._time_formatter_input.strip().lower() != "auto":
                raise ValueError("time_formatter string values must be 'auto'")
            self._time_formatter = _make_auto_tooltip_time_formatter(self._source_dates)
        elif callable(self._time_formatter_input):
            self._time_formatter = self._time_formatter_input
        else:
            raise TypeError("time_formatter must be callable, 'auto', or None")

    @property
    def y_axis(self) -> dcg.Axis:
        return self._y_axis

    @y_axis.setter
    def y_axis(self, value: dcg.Axis) -> None:
        self._y_axis = _validate_y_axis(value)
        axes = (dcg.Axis.X1, self._y_axis)
        self.axes = axes
        if self._volume_bar_series is not None:
            self._volume_bar_series.axes = axes

    def _volume_bar_weight(self) -> float:
        dates = np.asarray(self._dates, dtype=float)
        if dates.size > 1:
            deltas = np.diff(np.sort(dates[np.isfinite(dates)]))
            deltas = deltas[deltas > 0]
            if deltas.size:
                return float(np.median(deltas) * self._weight * 2.0)
        return max(self._weight * 2.0, np.finfo(float).eps)

    def _body_half_width(self) -> float:
        dates = np.asarray(self._dates, dtype=float)
        if dates.size > 1:
            return float(dates[1] - dates[0]) * float(self._weight)
        return float(self._weight)

    def _color_band_half_width(self) -> float:
        median_delta = _median_candle_delta_seconds(self._dates)
        if median_delta is not None:
            return median_delta * 0.5
        return abs(self._body_half_width())

    def get_candle_index_for_x(self, x_coord: float) -> int | None:
        dates = np.asarray(self._dates, dtype=float)
        if dates.size == 0:
            return None

        x_value = float(x_coord)
        if not np.isfinite(x_value):
            return None

        half_width = self._color_band_half_width()
        left = np.searchsorted(dates, x_value - half_width, side="left")
        right = np.searchsorted(dates, x_value + half_width, side="right")
        if left >= right:
            return None

        candidates = list(range(left, right))
        inside = [
            index for index in candidates
            if abs(float(dates[index]) - x_value) <= half_width
        ]
        if not inside:
            return None
        return min(inside, key=lambda index: abs(float(dates[index]) - x_value))

    def get_candle_direction_for_x(self, x_coord: float) -> str | None:
        index = self.get_candle_index_for_x(x_coord)
        if index is None:
            return None
        open_value = float(np.asarray(self._opens, dtype=float)[index])
        close_value = float(np.asarray(self._closes, dtype=float)[index])
        return "bullish" if close_value >= open_value else "bearish"

    def _normalized_volumes(self) -> np.ndarray:
        volumes = np.asarray(self._volumes, dtype=float)
        if volumes.size == 0:
            return np.array([], dtype=float)
        magnitudes = np.maximum(np.nan_to_num(volumes, nan=0.0, posinf=0.0, neginf=0.0), 0.0)
        maximum = float(np.max(magnitudes))
        if maximum <= 0.0:
            return np.zeros_like(magnitudes, dtype=float)
        return magnitudes / maximum

    def _volume_colors(self):
        if self._volume_color_override is not None:
            return self._volume_color_override
        opens = np.asarray(self._opens, dtype=float)
        closes = np.asarray(self._closes, dtype=float)
        return [
            self._bull_color if close >= open_ else self._bear_color
            for open_, close in zip(opens, closes)
        ]

    def _update_volume_series(self) -> None:
        if self._volume_bar_series is None:
            return
        dates = np.asarray(self._dates, dtype=float)
        normalized_volumes = self._normalized_volumes()
        colors = self._volume_colors()
        if normalized_volumes.size == 0:
            dates = np.array([], dtype=float)
            colors = []

        self._volume_bar_series.X = []
        self._volume_bar_series.Y = []
        self._volume_bar_series.colors = colors
        if self._volume_uses_default_weight:
            self._volume_bar_series.weight = self._volume_bar_weight()
        self._volume_bar_series.X = dates
        self._volume_bar_series.Y = normalized_volumes


    def render(self) -> None:
        count = self._dates.shape[0]
        width_percent = self._weight
        half_width = ((self._dates[1] - self._dates[0]) * width_percent) if count > 1 else width_percent
        self._clear_active_tooltip()
        self.children = []
        buttons = []
        with self:
            for i in range(count):
                open_pos = (self._dates[i] - half_width, self._opens[i])
                close_pos = (self._dates[i] + half_width, self._closes[i])
                low_pos = (self._dates[i], self._lows[i])
                high_pos = (self._dates[i], self._highs[i])
                color = self._bear_color if self._opens[i] > self._closes[i] else self._bull_color
                dcg.DrawLine(self.context, p1=low_pos, p2=high_pos, color=color, thickness=0.2*half_width)
                dcg.DrawRect(self.context, pmin=open_pos, pmax=close_pos, color=0, fill=color)
                buttons.append(
                    dcg.DrawInvisibleButton(self.context, button=0,
                                            p1=(open_pos[0], low_pos[1]),
                                            p2=(close_pos[0], high_pos[1]),
                                            user_data=(self._source_dates[i], self._opens[i],
                                                       self._closes[i], self._lows[i],
                                                       self._highs[i]))
                )
                
                # Render time counts if present
                if self._time_counts and i < len(self._time_counts):
                    counts = self._time_counts[i]
                    if counts and len(counts) > 0:
                        # Determine position (above high or below low)
                        if self._count_position == 'below':
                            base_y = self._lows[i]
                            direction = -1  # Move down
                        else:  # 'above' or default
                            base_y = self._highs[i]
                            direction = 1  # Move up
                        
                        # Render each count with vertical spacing
                        for j, count_val in enumerate(counts):
                            y_offset = direction * self._count_offset * (j + 1)
                            # Add half_width x-offset to center text on candle
                            #pos = (self._dates[i], base_y + y_offset)  # original
                            pos = (self._dates[i] - (half_width * 0.5), base_y + y_offset)
                            dcg.DrawText(
                                self.context,
                                pos=pos,
                                text=str(int(count_val)),
                                color=color
                            )
        for button in buttons:
            button.handlers = [
                dcg.GotHoverHandler(self.context, callback=self._tooltip_handler),
                dcg.LostHoverHandler(self.context, callback=self._tooltip_lost_handler),
            ]

    def _clear_active_tooltip(self) -> None:
        """Delete and reset the currently active managed tooltip, if any.

        This keeps tooltip ownership explicit and ensures render() or hover
        transitions cannot leave stale tooltip instances behind.
        """
        if self._active_tooltip is not None:
            try:
                self._active_tooltip.delete_item()
            except Exception:
                pass
        self._active_tooltip = None
        self._active_tooltip_target = None

    def _tooltip_handler(self, sender, target):
        """Create or reuse the candle tooltip for a hovered invisible button.

        The handler enforces a single-tooltip policy:
        - If the hovered target already owns the active tooltip, do nothing.
        - Otherwise, clear any previous tooltip and create a new one for target.

        This prevents duplicate OHLC rows during rare duplicate GotHover bursts.
        """
        if not self._tooltip:
            return
        if target is self._active_tooltip_target and self._active_tooltip is not None:
            return
        data = target.user_data
        self._clear_active_tooltip()
        with dcg.Tooltip(self.context, target=target,
                         parent=self.parent.parent) as tooltip:
            dcg.Text(self.context, value=f"Date: {self._time_formatter(data[0])}")
            dcg.Text(self.context, value=f"Open: {data[1]:.2f}")
            dcg.Text(self.context, value=f"Close: {data[2]:.2f}")
            dcg.Text(self.context, value=f"Low: {data[3]:.2f}")
            dcg.Text(self.context, value=f"High: {data[4]:.2f}")
        self._active_tooltip = tooltip
        self._active_tooltip_target = target

    def _tooltip_lost_handler(self, sender, target):
        """Clear the active tooltip when hover leaves its owning target."""
        if target is self._active_tooltip_target:
            self._clear_active_tooltip()


    def update_all(self, dates, opens, closes, lows, highs, volumes, time_counts=None, source_dates=None):
        """Set all arrays at once and re-render once.

        Raises:
            ValueError: if array lengths do not match.
        """
        if len(dates) != len(opens) or len(dates) != len(closes) \
        or len(dates) != len(lows) or len(dates) != len(highs):
            raise ValueError("dates, opens, closes, lows, highs must be of same length")
        if source_dates is None:
            source_dates = dates
        if len(source_dates) != len(dates):
            raise ValueError("source_dates must be the same length as dates")

        # assign all at once to avoid multiple render calls
        self._dates = dates
        self._source_dates = source_dates
        self._opens = opens
        self._closes = closes
        self._lows = lows
        self._highs = highs
        self._volumes = volumes
        self._refresh_time_formatter()
        if time_counts is not None:
            self._time_counts = time_counts
            self._validate_time_counts()

        self._update_volume_series()

        # rebuild the drawing primitives once
        self.render()

    # helper to apply partial updates and validate once
    def update(self, dates=None, opens=None, closes=None, lows=None, highs=None, volumes=None, time_counts=None, source_dates=None):
        """Update one or more series and re-render once. Validates lengths."""
        if dates is not None:
            self._dates = dates
        if source_dates is not None:
            self._source_dates = source_dates
        if opens is not None:
            self._opens = opens
        if closes is not None:
            self._closes = closes
        if lows is not None:
            self._lows = lows
        if highs is not None:
            self._highs = highs
        if volumes is not None:
            self._volumes = volumes
        if time_counts is not None:
            self._time_counts = time_counts

        self._refresh_time_formatter()

        self._validate_lengths()
        self._validate_time_counts()
        self._update_volume_series()
        
        self.render()


    def _validate_lengths(self):
        """Ensure that no arrays are empty and are not None."""
        series_names = ['dates', 'source_dates', 'opens', 'closes', 'lows', 'highs', 'volumes']
        arrays = [self._dates, self._source_dates, self._opens, self._closes, self._lows, self._highs, self._volumes]
        
        empty_series = []
        for name, arr in zip(series_names, arrays):
            if arr is None or len(arr) == 0:
                empty_series.append(name)
        
        if empty_series:
            raise ValueError(f"The following series must be non-empty: {', '.join(empty_series)}")
        
        """Ensure non-empty arrays have the same length."""
        lengths = [len(a) for a in arrays if a is not None]
        if lengths and len(set(lengths)) != 1:
            length_info = ', '.join([f"{name}={len(arr)}" for name, arr in zip(series_names, arrays) if arr is not None])
            raise ValueError(f"All series must have the same length. Current lengths: {length_info}")

    def _validate_time_counts(self):
        """Validate time_counts structure.
        
        time_counts is a list of lists where each element corresponds to a candle:
        - Structure: [[count1, count2, ...], [], [count3], ...]
        - Each sub-list contains 0-3 integers representing sequential indicator counts
        - Sub-lists can be empty [] (no counts for that candle)
        - Example valid structure for 5 candles:
            [[1, 2], [], [3], [1, 2, 3], [4]]
        - All elements must be numeric (int or convertible to int)
        - Top-level length must match number of candles in the series
        """
        if self._time_counts is None or len(self._time_counts) == 0:
            # Empty is valid (no counts to display)
            return
        
        # Check top-level length matches candle count
        if len(self._time_counts) != len(self._dates):
            raise ValueError(
                f"time_counts array length must match candle count. "
                f"Expected {len(self._dates)}, got {len(self._time_counts)}"
            )
        
        # Validate each sub-array
        for i, counts in enumerate(self._time_counts):
            if counts is None:
                continue
            # Convert to list if needed
            if not isinstance(counts, (list, tuple)):
                try:
                    counts = list(counts)
                except:
                    raise ValueError(
                        f"time_counts[{i}] must be a list-like structure, got {type(counts)}"
                    )
            
            # Check size (0-3 elements)
            if len(counts) > 3:
                raise ValueError(
                    f"each time_counts sub-array must contain 0-3 integers. "
                    f"time_counts[{i}] has {len(counts)} elements"
                )
            
            # Check all elements are numeric
            for j, val in enumerate(counts):
                try:
                    int(val)  # Test if convertible to int
                except (TypeError, ValueError):
                    raise ValueError(
                        f"time_counts[{i}][{j}] must be numeric, got {type(val).__name__}: {val}"
                    )

    # properties for nicer API
    @property
    def dates(self):
        return self._dates

    @dates.setter
    def dates(self, value):
        self._dates = value
        self._validate_lengths()
        self._update_volume_series()
        self.render()

    @property
    def source_dates(self):
        return self._source_dates

    @source_dates.setter
    def source_dates(self, value):
        self._source_dates = value
        self._refresh_time_formatter()
        self._validate_lengths()
        self.render()

    @property
    def opens(self):
        return self._opens

    @opens.setter
    def opens(self, value):
        self._opens = value
        self._validate_lengths()
        self._update_volume_series()
        self.render()

    @property
    def closes(self):
        return self._closes

    @closes.setter
    def closes(self, value):
        self._closes = value
        self._validate_lengths()
        self._update_volume_series()
        self.render()

    @property
    def lows(self):
        return self._lows

    @lows.setter
    def lows(self, value):
        self._lows = value
        self._validate_lengths()
        self.render()

    @property
    def highs(self):
        return self._highs

    @highs.setter
    def highs(self, value):
        self._highs = value
        self._validate_lengths()
        self.render()

    @property
    def volumes(self):
        return self._volumes

    @volumes.setter
    def volumes(self, value):
        self._volumes = value
        self._validate_lengths()
        self._update_volume_series()
        self.render()

    @property
    def time_counts(self):
        return self._time_counts

    @time_counts.setter
    def time_counts(self, value):
        self._time_counts = value
        self._validate_time_counts()
        self.render()

'''
    # convenience helpers (kept for backward compatibility) -> now use properties
    def update_dates(self, dates):
        """Update only the dates array and re-render."""
        self.dates = dates

    def update_opens(self, opens):
        """Update only the opens array and re-render."""
        self.opens = opens

    def update_closes(self, closes):
        """Update only the closes array and re-render."""
        self.closes = closes

    def update_lows(self, lows):
        """Update only the lows array and re-render."""
        self.lows = lows

    def update_highs(self, highs):
        """Update only the highs array and re-render."""
        self.highs = highs

    def update_volumes(self, volumes):
        """Update only the volumes array and re-render."""
        self.volumes = volumes
        
'''