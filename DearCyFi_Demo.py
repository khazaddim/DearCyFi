"""DearCyFi demo GUI.

Usage notes:
- Host apps feed fresh candle arrays into `DearCyFi` via `set_data(...)`.
- Time-collapse actions are invoked on the plot object (`collapse_time_chart`,
  `collapse_time_chart_vec`) instead of host-managed gap/locator objects.
"""

import asyncio
import importlib
from datetime import datetime

import dearcygui as dcg
from dearcygui.utils.asyncio_helpers import AsyncPoolExecutor, run_viewport_loop

try:
    DearCyFi = importlib.import_module("dearcyfi").DearCyFi
    generate_fake_candlestick_data = importlib.import_module(
        "dearcyfi.candle_utils.candle_gen"
    ).generate_fake_candlestick_data
except ModuleNotFoundError:
    from DearCyFi import DearCyFi
    from candle_utils.candle_gen import generate_fake_candlestick_data


loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)


class DearCyFiDemo:
    def __init__(self, white_theme: bool = False):
        self.C = dcg.Context()
        self.C.queue = AsyncPoolExecutor()
        self.C.viewport.wait_for_input = True

        if white_theme:
            self.C.viewport.initialize(height=900, width=1600, theme=self._white_theme())
        else:
            self.C.viewport.initialize(height=900, width=1600)

        with dcg.Window(self.C, label="DearCyFi Demo", primary=True, width="fillx", height="filly") as main_window:
            with dcg.HorizontalLayout(self.C, no_wrap=True):
                with dcg.ChildWindow(self.C, label="Left Side", width=320, resizable_x=True) as self.left_win:
                    self.plot_button = dcg.Button(
                        self.C,
                        label="Plot Candle Data",
                        width="fillx",
                        height='main_window.height/24+10', #32
                        callback=self.plot_candle_data,
                    )
                    self.gaps_button = dcg.Button(
                        self.C,
                        label="Gaps n' Chunks",
                        width="fillx",
                        height='main_window.height/24+10', #32
                        callback=lambda s, a, u: self.DCF_plot.add_gaps_chunks_GUI(s, a, u),
                    )
                    self.collapse_button = dcg.Button(
                        self.C,
                        label="Collapse Time",
                        width="fillx",
                        height='main_window.height/24+10', #32
                        callback=lambda s, a, u: self.DCF_plot.collapse_time_chart(s, a, u),
                    )
                    self.collapse_vec_button = dcg.Button(
                        self.C,
                        label="Collapse Time Vec",
                        width="fillx",
                        height='main_window.height/24+10', #32
                        callback=lambda s, a, u: self.DCF_plot.collapse_time_chart_vec(s, a, u),
                    )
                    self.load_bars_button = dcg.Button(
                        self.C,
                        label="Load Bar Data",
                        width="fillx",
                        height='main_window.height/24+10', #32
                        callback=lambda s, a, u: self.DCF_plot.load_horizontal_bars(s, a, u),
                    )

                    self.status_text = dcg.SharedStr(
                        self.C,
                        value=(
                            "DearCyFi demo loaded.\n"
                            "Click 'Plot Candle Data' to load synthetic candles."
                        ),
                    )
                    self.status_label = dcg.Text(
                        self.C,
                        shareable_value=self.status_text,
                        wrap=300,
                        height="filly",
                    )

                with dcg.ChildWindow(self.C, label="Right Side"):
                    with dcg.TabBar(self.C):
                        with dcg.Tab(self.C, label="Collapsed Time Chart"):
                            self.DCF_plot = DearCyFi(
                                self.C,
                                label="DearCyFi Plot",
                                width="fillx",
                                height="filly",
                                has_box_select=True,
                                on_status=self.set_status,
                            )

                        with dcg.Tab(self.C, label="Original Time Chart"):
                            with dcg.Plot(self.C, label="Original Time Plot", width="fillx", height="filly", has_box_select=True) as self.orig_plot:
                                self.orig_plot.X1.label = "Date"
                                self.orig_plot.X1.scale = dcg.AxisScale.TIME
                                self.orig_plot.Y1.label = "Price ($)"

        self.left_win.handlers += [
            dcg.ResizeHandler(self.C, callback=self.on_resize)
        ]

        self.plot_candle_data(None, None, None)

    def _white_theme(self):
        viewport_theme = dcg.ThemeColorImGui(
            self.C,
            border_shadow=(0.960784375667572, 0.960784375667572, 0.960784375667572, 0.0),
            window_bg=(0.9490196704864502, 0.9058824181556702, 0.9058824181556702, 0.9411765336990356),
            title_bg=(0.9803922176361084, 0.9803922176361084, 0.9803922176361084, 1.0),
            text=(0.1, 0.9, 0.14509804546833038, 1.0),
        )
        plot_theme = dcg.ThemeColorImPlot(
            self.C,
            axis_grid=(0.07450980693101883, 0.06666667014360428, 0.06666667014360428, 0.250980406999588),
        )
        theme = dcg.ThemeList(self.C)
        theme.children = [viewport_theme, plot_theme]
        return theme

    def set_status(self, text: str) -> None:
        self.status_text.value = str(text)
        self.C.viewport.wake()

    def on_resize(self, sender, app_data):
        self.status_label.wrap = app_data.width.value - 80

    def plot_candle_data(self, sender, app_data, user_data):
        dates, opens, highs, lows, closes, index, volume = generate_fake_candlestick_data(
            remove_weekends=True,
            interval="hourly",
            length=500,
        )

        self.DCF_plot.set_data(
            dates=dates,
            opens=opens,
            highs=highs,
            lows=lows,
            closes=closes,
            index=index,
            volume=volume,
            time_formatter=lambda x: datetime.fromtimestamp(x).strftime("%b %d"),
        )

        orig_dates, orig_opens, orig_highs, orig_lows, orig_closes, _, orig_volume = generate_fake_candlestick_data(
            remove_weekends=True,
            interval="hourly",
            length=300,
        )
        if not hasattr(self, "orig_candlestick"):
            try:
                PlotCandleStick = importlib.import_module("dearcyfi.DCG_Candle_Utils").PlotCandleStick
            except ModuleNotFoundError:
                from DCG_Candle_Utils import PlotCandleStick

            with self.orig_plot:
                self.orig_candlestick = PlotCandleStick(
                    self.C,
                    dates=orig_dates,
                    opens=orig_opens,
                    closes=orig_closes,
                    lows=orig_lows,
                    highs=orig_highs,
                    label="Stock Price",
                    weight=0.1,
                    time_formatter=lambda x: datetime.fromtimestamp(x).strftime("%b %d"),
                )
        else:
            self.orig_candlestick.update_all(
                dates=orig_dates,
                opens=orig_opens,
                closes=orig_closes,
                lows=orig_lows,
                highs=orig_highs,
                volumes=orig_volume,
            )

        self.set_status("Loaded fresh candle data into DearCyFi.")


if __name__ == "__main__":
    app = DearCyFiDemo(white_theme=False)
    try:
        loop.run_until_complete(run_viewport_loop(app.C.viewport))
    finally:
        print("DearCyFi demo closed.")
