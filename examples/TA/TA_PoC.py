"""DearCyFi Technical indicators and overlays proof of concept demo.
"""

import asyncio
import importlib
from datetime import datetime

import dearcygui as dcg
from dearcygui.utils import DateTimePicker
from dearcygui.utils.asyncio_helpers import AsyncPoolExecutor, run_viewport_loop

from dearcyfi import DearCyFi

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

        with dcg.Window(self.C, label="TA Proof of Concept", primary=True, width="fillx", height="filly") as main_window:
            test_plot= dcg.Plot(self.C, label="TA_Tests", width="fillx", height="filly")


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



if __name__ == "__main__":
    app = DearCyFiDemo(white_theme=False)
    try:
        loop.run_until_complete(run_viewport_loop(app.C.viewport))
    except KeyboardInterrupt:
        print("Got the strange window close keyboard interrupt bug. Exiting TA demo.")
    finally:
        # Cancel any lingering async tasks so the loop can shut down cleanly.
        for task in asyncio.all_tasks(loop):
            task.cancel()
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
        print("TA demo closed.")
