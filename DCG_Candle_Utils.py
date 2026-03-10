import datetime
import dearcygui as dcg
from collections.abc import Sized

class PlotCandleStick(dcg.DrawInPlot):
    """
    Adds a candle series to a plot.

    See the source code for how to make
    a custom version with more interactions.

    Volume Scaling Note:
        Volume data is plotted on the same Y-axis as price data, making it a relative
        representation of volume. For proper visualization, volume values should be 
        scaled so that the maximum volume is approximately 20% of the price range 
        (max_high - min_low). This ensures volume bars are confined to the bottom 
        portion of the chart without obscuring price data.
        
        If volume data exceeds this threshold, a warning will be printed and the data
        will be automatically normalized to fit within the recommended scale.
        
        Example: For price range 100-150 (range=50), max volume should be ~10 (20% of 50).

    Args:
        dates (np.ndarray): x-axis values
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
        time_formatter (callback, optional): callback that takes a date and returns a string
    """
    def __init__(self,
                 context : dcg.Context,
                 no_legend=False,
                 dates: Sized = [],
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
                 **kwargs) -> None:
        super().__init__(context, **kwargs)
        # For DrawInPlot, default no_legend is True
        # Thus the override.
        self.no_legend = no_legend
        # normalize volumes default
        if volumes is None:
            volumes = []
        # normalize time_counts default
        if time_counts is None:
            time_counts = []
        # basic length check (volumes optional)
        if len(dates) != len(opens) or len(dates) != len(closes) \
           or len(dates) != len(lows) or len(dates) != len(highs):
            raise ValueError("dates, opens, closes, lows, highs must be of same length")
        # Same to local variables
        self._dates = dates
        self._opens = opens
        self._closes = closes
        self._lows = lows
        self._highs = highs
        self._volumes = volumes
        self._time_counts = time_counts
        self._count_position = count_position
        self._count_offset = count_offset
        # volume item handling
        self._volume_digital_series = None
        self._volume_kwargs = volume_kwargs or {}
        try:
            self._volume_digital_series = dcg.PlotDigital(context, X=self._dates, Y=self._volumes, **self._volume_kwargs)
        except Exception as e:
            # fail gracefully; keep None
            print(f"Couldn't create internal PlotDigital: {e}")

        self._bull_color = dcg.color_as_int(bull_color)
        self._bear_color = dcg.color_as_int(bear_color)
        self._weight = float(weight)
        self._tooltip = tooltip

        # Validate and normalize volume data if needed
        self._normalize_volumes_if_needed()

        self._time_formatter = time_formatter
        if time_formatter is None:
            # use datetime:
            self._time_formatter = lambda x: datetime.datetime.fromtimestamp(x).strftime('%Y-%m-%d %H:%M:%S')

        self.render()


    def render(self) -> None:
        count = self._dates.shape[0]
        width_percent = self._weight
        half_width = ((self._dates[1] - self._dates[0]) * width_percent) if count > 1 else width_percent
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
                                            user_data=(self._dates[i], self._opens[i],
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
        tooltip_handler = dcg.GotHoverHandler(self.context, callback=self._tooltip_handler)
        # Here add your handlers to the buttons to react to clicks, etc
        for button in buttons:
            button.handlers = [tooltip_handler]

    def _tooltip_handler(self, sender, target):
        data = target.user_data
        if self._tooltip:
            with dcg.utils.TemporaryTooltip(self.context, target=target,
                                            parent=self.parent.parent):
                dcg.Text(self.context, value=f"Date: {self._time_formatter(data[0])}")
                dcg.Text(self.context, value=f"Open: {data[1]}")
                dcg.Text(self.context, value=f"Close: {data[2]}")
                dcg.Text(self.context, value=f"Low: {data[3]}")
                dcg.Text(self.context, value=f"High: {data[4]}")


    def update_all(self, dates, opens, closes, lows, highs, volumes, time_counts=None):
        """Set all arrays at once and re-render once.

        Raises:
            ValueError: if array lengths do not match.
        """
        if len(dates) != len(opens) or len(dates) != len(closes) \
        or len(dates) != len(lows) or len(dates) != len(highs):
            raise ValueError("dates, opens, closes, lows, highs must be of same length")

        # assign all at once to avoid multiple render calls
        self._dates = dates
        self._opens = opens
        self._closes = closes
        self._lows = lows
        self._highs = highs
        self._volumes = volumes
        if time_counts is not None:
            self._time_counts = time_counts
            self._validate_time_counts()

        # Validate and normalize volume data if needed
        self._normalize_volumes_if_needed()

        # update attached PlotDigital
        self._volume_digital_series.X = self._dates
        self._volume_digital_series.Y = self._volumes

        # rebuild the drawing primitives once
        self.render()

    # helper to apply partial updates and validate once
    def update(self, dates=None, opens=None, closes=None, lows=None, highs=None, volumes=None, time_counts=None):
        """Update one or more series and re-render once. Validates lengths."""
        if dates is not None:
            self._dates = dates
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

        self._validate_lengths()
        self._validate_time_counts()
        # Validate and normalize volume data if needed
        self._normalize_volumes_if_needed()
        # keep volume plot in sync for partial updates
        self._volume_digital_series.Y = self._volumes
        self._volume_digital_series.X = self._dates
        
        self.render()


    def _validate_lengths(self):
        """Ensure that no arrays are empty and are not None."""
        series_names = ['dates', 'opens', 'closes', 'lows', 'highs', 'volumes']
        arrays = [self._dates, self._opens, self._closes, self._lows, self._highs, self._volumes]
        
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

    def _normalize_volumes_if_needed(self):
        """Check if volume data needs normalization and apply if necessary.
        
        Volume should be scaled so max volume ≈ 20% of price range for proper visualization.
        If volume amplitude is too large, normalize it and print a warning.
        """
        import numpy as np
        
        # Skip if no volume data or empty arrays
        if self._volumes is None or len(self._volumes) == 0:
            return
        if len(self._highs) == 0 or len(self._lows) == 0:
            return
        
        # Calculate price range
        price_max = float(np.max(self._highs))
        price_min = float(np.min(self._lows))
        price_range = price_max - price_min
        
        if price_range <= 0:
            return  # Can't normalize with zero or negative range
        
        # Calculate volume range
        volume_max = float(np.max(self._volumes))
        volume_min = float(np.min(self._volumes))
        
        # Target: max volume should be ~20% of price range
        target_max = price_range * 0.20
        
        # Check if normalization is needed (threshold: if max volume > 3x price range)
        # This only catches severely mis-scaled data (e.g., volumes in thousands for prices ~100)
        # while allowing reasonable variations in volume scale
        normalization_threshold = price_range * 3.0
        
        if volume_max > normalization_threshold:
            # Calculate scaling factor
            scale_factor = target_max / volume_max
            
            # Apply normalization
            self._volumes = np.array(self._volumes) * scale_factor
            
            print(f"[PlotCandleStick] Warning: Volume data amplitude too large for price scale.")
            print(f"  Price range: {price_min:.2f} - {price_max:.2f} (range: {price_range:.2f})")
            print(f"  Original volume range: {volume_min:.2f} - {volume_max:.2f}")
            print(f"  Normalized volume to: {float(np.min(self._volumes)):.2f} - {float(np.max(self._volumes)):.2f}")
            print(f"  Applied scale factor: {scale_factor:.6f}")
            print(f"  Recommendation: Pre-scale volume data to max ~{target_max:.2f} for this price range.")

    # properties for nicer API
    @property
    def dates(self):
        return self._dates

    @dates.setter
    def dates(self, value):
        self._dates = value
        self._validate_lengths()
        self._volume_digital_series.X = self._dates
        self.render()

    @property
    def opens(self):
        return self._opens

    @opens.setter
    def opens(self, value):
        self._opens = value
        self._validate_lengths()
        self.render()

    @property
    def closes(self):
        return self._closes

    @closes.setter
    def closes(self, value):
        self._closes = value
        self._validate_lengths()
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