

User: when #file:core.py passes dates to #sym:candlestick_plot those are initially the original dates, then when the user askes the program to collapse the dates to removes weekend gaps in the candle chart, for example, #sym:collapse_time_chart is called and then the dates are replaced with the collapsed dates.  Those dates are however shifted and not correct, that is why we have the visual axes labels rewritten in #sym:axes_resize_callback .  We just perform this date collapse so that we can have the candles all be next to each other with the limitations inherent in implot.  The issue here is that the tooltips displayed in #file:DCG_Candle_Utils.py are then shifted and incorrect.  I think we may need to have 2 date fields passed to #sym:candlestick_plot , one that is shifted for the positions of the candles, and one that is not so the labels can be correctly displayed.  What do you think, does that solution make sense?

GitHub Copilot: That diagnosis makes sense at first glance, and I’m going to trace the candle data path before recommending the exact shape. I’ll check how `PlotCandleStick` stores dates for drawing, hit testing, updates, and tooltip formatting so we can separate display-time from plot-position without surprising side effects.

Read [](DearCyFi/src/dearcyfi/DCG_Candle_Utils.py#1-1), lines 1 to 430

Read [](DearCyFi/src/dearcyfi/core.py#300-300), lines 300 to 430

Read [](DearCyFi/src/dearcyfi/core.py#470-470), lines 470 to 742

Yes, that solution makes sense. In fact, it is probably the cleanest fix.

Right now `PlotCandleStick` uses one `dates` array for two different meanings:

1. Candle geometry: `DrawLine`, `DrawRect`, `DrawInvisibleButton` positions.
2. Semantic timestamp: tooltip `Date: ...`.

After `collapse_time_chart()` runs, those meanings diverge. The collapsed values are correct for candle placement, but wrong as real timestamps. So the candle plot needs separate arrays, something like:

- `dates` or `x_dates`: collapsed/display x-coordinates used for drawing.
- `tooltip_dates`, `source_dates`, or `real_dates`: original timestamps used for tooltip text.

I would slightly prefer naming them by responsibility:

```python
dates          # x positions used by ImPlot / drawing
display_dates  # real timestamps shown in tooltip
```

or, even clearer:

```python
plot_dates     # shifted/collapsed x positions
source_dates   # original timestamps
```

The key place is DCG_Candle_Utils.py: `render()` should continue using the collapsed plot dates for positions, but the invisible button `user_data` should store the original/source date for tooltip display.

Conceptually:

```python
user_data=(
    self._tooltip_dates[i],
    self._opens[i],
    self._closes[i],
    self._lows[i],
    self._highs[i],
)
```

while all positions still use:

```python
self._dates[i]
```

Then core.py can initially pass the same original dates as both arrays. When collapsing, it updates only the plot-position dates, while leaving tooltip/source dates alone.

There is an alternative where the tooltip formatter expands collapsed dates back through `time_map.expand()`, but I like your two-date-field idea better. It keeps `PlotCandleStick` dumb and local: geometry dates are geometry dates, tooltip dates are tooltip dates. No need for the candle renderer to know about gap maps, collapsed axes, or weekend-removal logic.