import numpy as np
import dearcygui as dcg
from collections.abc import Sized


class PlotHorizontalBars(dcg.DrawInPlot):
    """
    Adds a horizontal bar series to a plot.
    
    Bars extend horizontally from the right edge of the plot leftward,
    positioned at specific Y coordinates. Dynamically updates positions
    via AxesResizeHandler to maintain alignment during zoom/pan.
    
    Based on the pattern from horizontal_bars.py demo.

    Args:
        context (dcg.Context): DearCyGui context
        X (np.ndarray): Bar lengths or offsets from right edge
        Y (np.ndarray): Y-axis positions for each bar
        bar_height (float, optional): Height of each bar. Defaults to 0.1
        spacing (float, optional): Spacing between bars (currently unused, reserved for future). Defaults to 0.0
        color (tuple, optional): RGBA color tuple. Defaults to None (uses theme)
        theme (dcg.ThemeList, optional): DearCyGui theme for styling. Defaults to None
        **kwargs: Additional arguments passed to dcg.DrawInPlot

    Example:
        >>> # Create horizontal bars at different Y positions
        >>> bar_lengths = np.array([1.5, 2.3, 1.8, 2.7])
        >>> y_positions = np.array([100, 110, 120, 130])
        >>> bars = PlotHorizontalBars(
        ...     context=C,
        ...     X=bar_lengths,
        ...     Y=y_positions,
        ...     bar_height=0.5,
        ...     theme=my_theme
        ... )
    """
    
    def __init__(self,
                 context: dcg.Context,
                 X: Sized = [],
                 Y: Sized = [],
                 axis_x_max: float = None,
                 bar_height: float = None,
                 spacing: float = 0.0,
                 color: tuple = None,
                 theme: dcg.ThemeList = None,
                 **kwargs) -> None:
        """
        Args:
            context (dcg.Context): DearCyGui context
            X (np.ndarray): Bar lengths or offsets from right edge
            Y (np.ndarray): Y-axis positions for each bar
            axis_x_max (float): Current maximum X value of the plot's X axis (required)
            bar_height (float, optional): Height of each bar. Defaults to 0.1
            spacing (float, optional): Spacing between bars (currently unused). Defaults to 0.0
            color (tuple, optional): RGBA color tuple. Defaults to None (uses theme)
            theme (dcg.ThemeList, optional): DearCyGui theme for styling. Defaults to None
            **kwargs: Additional arguments passed to dcg.DrawInPlot
        """
        super().__init__(context, **kwargs)

        if axis_x_max is None:
            raise ValueError("axis_x_max must be provided to PlotHorizontalBars for correct initial rendering.")

        # Validate input arrays
        if len(X) != len(Y):
            raise ValueError(f"X and Y arrays must have same length. Got X={len(X)}, Y={len(Y)}")


        # Store data
        self._X = np.array(X, dtype=float)
        self._Y = np.array(Y, dtype=float)
        self._spacing = float(spacing)
        self._color = color
        self._theme = theme

        # Auto-calculate bar_height if not provided
        if bar_height is None:
            if len(self._Y) > 1:
                # Sort Y to get spacing between adjacent bars
                sorted_y = np.sort(self._Y)
                diffs = np.diff(sorted_y)
                min_spacing = np.min(diffs)
                # Use 95% of the minimum spacing to avoid overlap
                self._bar_height = min_spacing * 0.95
            else:
                self._bar_height = 0.1  # fallback default
        else:
            self._bar_height = float(bar_height)

        # Storage for bar objects and parameters
        self._bar_objs = []
        self._bar_params = []  # List of (x_offset, y_center, height) tuples

        # Current axis max (updated by callback)
        self._current_axis_x_max = axis_x_max

        self.render()
    
    def render(self) -> None:
        """
        Creates DrawRect objects for each horizontal bar.
        Bars are initially positioned at a default location until
        axis callback provides the actual axis_x_max.
        """
        # Clear existing bars
        self.children = []
        self._bar_objs = []
        self._bar_params = []
        
        if len(self._X) == 0:
            return
        
        # axis_x_max is now always set by constructor
        
        with self:
            for i in range(len(self._X)):
                x_offset = self._X[i]
                y_center = self._Y[i]
                height = self._bar_height
                
                # Store parameters for dynamic updates
                self._bar_params.append((x_offset, y_center, height))
                
                # Calculate rectangle bounds
                # Horizontal bars: extend from (axis_x_max - x_offset) to axis_x_max
                pmin = (self._current_axis_x_max - x_offset, y_center - height / 2)
                pmax = (self._current_axis_x_max, y_center + height / 2)
                
                # Determine color
                if self._color is not None:
                    fill_color = self._color
                else:
                    # Default red with transparency
                    fill_color = (255, 0, 0, 100)
                
                # Create the bar rectangle
                rect = dcg.DrawRect(
                    self.context,
                    pmin=pmin,
                    pmax=pmax,
                    color=0,
                    fill=fill_color,
                    rounding=0.2,
                    thickness=0.1
                )
                
                # Apply theme if provided
                if self._theme is not None:
                    rect.theme = self._theme
                
                self._bar_objs.append(rect)
    
    def update(self, X=None, Y=None):
        """
        Updates the bar data and re-renders.
        
        Args:
            X (array-like, optional): New X values (bar lengths)
            Y (array-like, optional): New Y values (positions)
        """
        if X is not None:
            self._X = np.array(X, dtype=float)
        if Y is not None:
            self._Y = np.array(Y, dtype=float)
        
        # Validate lengths
        if len(self._X) != len(self._Y):
            raise ValueError(f"X and Y arrays must have same length. Got X={len(self._X)}, Y={len(self._Y)}")
        
        self.render()
    
    def update_positions(self, axis_x_max):
        """
        Updates bar positions based on current axis X max value.
        Called by AxesResizeHandler callback.
        
        Args:
            axis_x_max (float): Current maximum X value of the axis
        """
        self._current_axis_x_max = axis_x_max
        
        # Update each bar's position
        for rect, (x_offset, y_center, height) in zip(self._bar_objs, self._bar_params):
            rect.pmin = (axis_x_max - x_offset, y_center - height / 2)
            rect.pmax = (axis_x_max, y_center + height / 2)



def generate_sample_bar_data(num_bars=20, y_min=0, y_max=100, x_min=0.5, x_max=3.0):
    """
    Generate sample data for horizontal bars.
    
    Args:
        num_bars (int): Number of bars to generate
        y_min (float): Minimum Y position
        y_max (float): Maximum Y position
        x_min (float): Minimum bar length
        x_max (float): Maximum bar length
    
    Returns:
        tuple: (X, Y) arrays for bar lengths and positions
    """
    Y = np.linspace(y_min, y_max, num_bars)
    X = np.random.uniform(x_min, x_max, size=num_bars)
    return X, Y
