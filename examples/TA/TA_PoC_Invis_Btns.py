"""DearCyFi Technical indicators and overlays proof of concept demo.
"""

import asyncio
import importlib
from datetime import datetime

import dearcygui as dcg
from dearcygui.utils import DateTimePicker
from dearcygui.utils.asyncio_helpers import AsyncPoolExecutor, run_viewport_loop

from dearcyfi import DearCyFi

from dearcyfi.candle_utils.candle_gen import generate_fake_candlestick_data

from dearcyfi.DCG_Candle_Utils import PlotCandleStick

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)


class MovableResizableBoxIndicator:
    def __init__(
        self,
        context,
        *,
        layer,
        status,
        p1,
        p2,
        label: str = "Movable range box",
        color=(50, 140, 255, 255),
        hover_color=(255, 170, 60, 255),
        active_color=(255, 210, 120, 255),
        fill=(50, 140, 255, 80),
        hover_fill=(255, 170, 60, 110),
        active_fill=(255, 190, 80, 125),
        min_width: float = 1.0,
        min_height: float = 1.0,
        handle_half_width: float | None = None,
        handle_half_height: float | None = None,
        hit_size: float = 24.0,
        allow_inversion: bool = False,
    ):
        self.C = context
        self.status = status
        self.label_text = label
        self.color = color
        self.hover_color = hover_color
        self.active_color = active_color
        self.fill = fill
        self.hover_fill = hover_fill
        self.active_fill = active_fill
        self.min_width = float(min_width)
        self.min_height = float(min_height)
        self.hit_size = float(hit_size)
        self.allow_inversion = bool(allow_inversion)
        self.p1 = [float(min(p1[0], p2[0])), float(min(p1[1], p2[1]))]
        self.p2 = [float(max(p1[0], p2[0])), float(max(p1[1], p2[1]))]
        initial_width = self.p2[0] - self.p1[0]
        initial_height = self.p2[1] - self.p1[1]
        self.handle_half_width = (
            float(handle_half_width) if handle_half_width is not None else max(initial_width * 0.035, self.min_width * 0.08)
        )
        self.handle_half_height = (
            float(handle_half_height) if handle_half_height is not None else max(initial_height * 0.12, self.min_height * 0.18)
        )
        self.backup_p1 = self.p1.copy()
        self.backup_p2 = self.p2.copy()
        self.active_handle = None
        self.hover_handle = None
        self.was_dragging = False

        with layer:
            self.rect = dcg.DrawRect(
                context,
                pmin=tuple(self.p1),
                pmax=tuple(self.p2),
                color=self.color,
                fill=self.fill,
                thickness=2,
            )
            self.label = dcg.DrawText(
                context,
                pos=(self.p1[0], self.p2[1]),
                text=self.label_text,
                color=(255, 255, 255, 255),
                size=14,
            )
            self.center_button = dcg.DrawInvisibleButton(
                context,
                p1=tuple(self.p1),
                p2=tuple(self.p2),
                button=dcg.MouseButtonMask.ANY,
                capture_mouse=True,
            )
            self.handle_rects = {}
            self.handle_buttons = {}
            for handle_name in ("tl", "tr", "bl", "br"):
                center_x, center_y = self._handle_center(handle_name)
                self.handle_rects[handle_name] = dcg.DrawRect(
                    context,
                    pmin=(center_x, center_y),
                    pmax=(center_x, center_y),
                    color=(255, 255, 255, 255),
                    fill=(20, 20, 20, 220),
                    thickness=1,
                )
                self.handle_buttons[handle_name] = dcg.DrawInvisibleButton(
                    context,
                    p1=(center_x, center_y),
                    p2=(center_x, center_y),
                    min_side=self.hit_size,
                    button=dcg.MouseButtonMask.ANY,
                    capture_mouse=True,
                )

        self.center_button.handlers = self._build_handlers("move", dcg.MouseCursor.RESIZE_ALL)
        for handle_name, button in self.handle_buttons.items():
            button.handlers = self._build_handlers(handle_name, self._cursor_for_handle(handle_name))
        self.update_draw_items()

    def _build_handlers(self, handle_name: str, cursor) -> list:
        cursor_on_hover = dcg.ConditionalHandler(self.C)
        with cursor_on_hover:
            dcg.MouseCursorHandler(self.C, cursor=cursor)
            dcg.HoverHandler(self.C)

        return [
            dcg.GotHoverHandler(self.C, callback=lambda *_args: self._handle_hover_enter(handle_name)),
            dcg.LostHoverHandler(self.C, callback=lambda *_args: self._handle_hover_leave(handle_name)),
            dcg.ClickedHandler(self.C, callback=lambda *_args: self._handle_clicked(handle_name)),
            dcg.DraggingHandler(self.C, callback=lambda _sender, _target, delta: self._handle_dragging(handle_name, delta)),
            dcg.DraggedHandler(self.C, callback=lambda _sender, _target, delta: self._handle_dragged(handle_name, delta)),
            cursor_on_hover,
        ]

    def _cursor_for_handle(self, handle_name: str):
        if handle_name in ("tl", "br"):
            return dcg.MouseCursor.RESIZE_NWSE
        return dcg.MouseCursor.RESIZE_NESW

    def _handle_center(self, handle_name: str) -> tuple[float, float]:
        x_coord = self.p1[0] if "l" in handle_name else self.p2[0]
        y_coord = self.p1[1] if "b" in handle_name else self.p2[1]
        return x_coord, y_coord

    def update_draw_items(self) -> None:
        x_min = min(self.p1[0], self.p2[0])
        x_max = max(self.p1[0], self.p2[0])
        y_min = min(self.p1[1], self.p2[1])
        y_max = max(self.p1[1], self.p2[1])

        self.rect.pmin = (x_min, y_min)
        self.rect.pmax = (x_max, y_max)
        self.label.pos = (x_min, y_max)

        width = x_max - x_min
        height = y_max - y_min
        x_pad = width * 0.12
        y_pad = height * 0.18
        self.center_button.p1 = (x_min + x_pad, y_min + y_pad)
        self.center_button.p2 = (x_max - x_pad, y_max - y_pad)

        for handle_name, handle_rect in self.handle_rects.items():
            center_x, center_y = self._handle_center(handle_name)
            handle_rect.pmin = (center_x - self.handle_half_width, center_y - self.handle_half_height)
            handle_rect.pmax = (center_x + self.handle_half_width, center_y + self.handle_half_height)
            handle_rect.fill = self._handle_fill(handle_name)
            button = self.handle_buttons[handle_name]
            button.p1 = (center_x, center_y)
            button.p2 = (center_x, center_y)

    def _handle_fill(self, handle_name: str):
        if handle_name == self.active_handle:
            return (255, 190, 80, 255)
        if handle_name == self.hover_handle:
            return (255, 230, 120, 255)
        return (20, 20, 20, 220)

    def _handle_hover_enter(self, handle_name: str) -> None:
        if not self.was_dragging:
            self.hover_handle = handle_name
        self.rect.fill = self.hover_fill
        self.rect.color = self.hover_color
        self.update_draw_items()
        self.status.value = self._status_for_hover(handle_name)
        self.C.viewport.wake()

    def _handle_hover_leave(self, handle_name: str) -> None:
        if self.was_dragging or self.active_handle == handle_name:
            return
        if self.hover_handle == handle_name:
            self.hover_handle = None
        self.rect.fill = self.fill
        self.rect.color = self.color
        self.update_draw_items()
        self.status.value = "Drag inside the box to move it, or drag a corner handle to resize it."
        self.C.viewport.wake()

    def _handle_clicked(self, handle_name: str) -> None:
        self.active_handle = handle_name
        self.hover_handle = handle_name
        self.backup_p1 = self.p1.copy()
        self.backup_p2 = self.p2.copy()
        self.update_draw_items()
        self.status.value = self._status_for_start(handle_name)
        self.C.viewport.wake()

    def _handle_dragging(self, handle_name: str, delta) -> None:
        if not self.was_dragging or self.active_handle != handle_name:
            self.backup_p1 = self.p1.copy()
            self.backup_p2 = self.p2.copy()
            self.active_handle = handle_name
            self.hover_handle = handle_name
            self.was_dragging = True

        self._apply_drag(handle_name, delta)
        self.rect.fill = self.active_fill
        self.rect.color = self.active_color
        self.status.value = self._status_for_drag(handle_name)
        self.C.viewport.wake()

    def _handle_dragged(self, handle_name: str, delta) -> None:
        if self.was_dragging:
            self._apply_drag(handle_name, delta)
        self.was_dragging = False
        self.active_handle = None
        self.hover_handle = handle_name
        self.rect.fill = self.hover_fill
        self.rect.color = self.hover_color
        self.update_draw_items()
        self.status.value = "Box interaction released. Drag the body or a corner handle again."
        self.C.viewport.wake()

    def _apply_drag(self, handle_name: str, delta) -> None:
        dx, dy = float(delta[0]), float(delta[1])
        left, bottom = self.backup_p1
        right, top = self.backup_p2

        if handle_name == "move":
            left += dx
            right += dx
            bottom += dy
            top += dy
        else:
            if "l" in handle_name:
                left += dx
            if "r" in handle_name:
                right += dx
            if "b" in handle_name:
                bottom += dy
            if "t" in handle_name:
                top += dy

            if not self.allow_inversion:
                if right - left < self.min_width:
                    if "l" in handle_name:
                        left = right - self.min_width
                    else:
                        right = left + self.min_width
                if top - bottom < self.min_height:
                    if "b" in handle_name:
                        bottom = top - self.min_height
                    else:
                        top = bottom + self.min_height

        self.p1 = [left, bottom]
        self.p2 = [right, top]
        self.update_draw_items()

    def _status_for_hover(self, handle_name: str) -> str:
        if handle_name == "move":
            return "Hovering box body. Drag to move the indicator."
        return f"Hovering corner handle {handle_name}. Drag to resize the indicator."

    def _status_for_start(self, handle_name: str) -> str:
        if handle_name == "move":
            return "Move started from the box body."
        return f"Resize started from {handle_name}."

    def _status_for_drag(self, handle_name: str) -> str:
        action = "Moving" if handle_name == "move" else f"Resizing {handle_name}"
        flip_state = " inverted" if self.p1[0] > self.p2[0] or self.p1[1] > self.p2[1] else ""
        return (
            f"{action}{flip_state}: x1={self.p1[0]:.0f}, x2={self.p2[0]:.0f}, "
            f"y1={self.p1[1]:.2f}, y2={self.p2[1]:.2f}"
        )


class TA_Demo:
    def __init__(self, white_theme: bool = False):
        self.C = dcg.Context()
        self.C.queue = AsyncPoolExecutor()
        self.C.viewport.wait_for_input = True

        if white_theme:
            self.C.viewport.initialize(height=900, width=1600, theme=self._white_theme())
        else:
            self.C.viewport.initialize(height=900, width=1600)

        with dcg.Window(self.C, label="TA Proof of Concept", primary=True, width="fillx", height="filly") as main_window:
            with dcg.VerticalLayout(self.C, width="fillx", height="filly"):
                dcg.Text(
                    self.C,
                    value="Backdrop candles plus a movable, resizable technical-indicator box built from invisible hit regions.",
                )
                self.overlay_status = dcg.Text(
                    self.C,
                    value="Drag inside the box to move it, or drag a corner handle to resize it.",
                )

                with dcg.Plot(self.C, label="TA Plot", width="fillx", height="filly", has_box_select=True) as self.Test_plot:
                    self.Test_plot.X1.label = "Date"
                    self.Test_plot.X1.scale = dcg.AxisScale.TIME
                    self.Test_plot.Y1.label = "Price ($)"

                    self._load_backdrop_candles()

    def _load_backdrop_candles(self) -> None:
        # Keep a light candle backdrop so the TA overlay work has an axis range to fit against.
        dates, opens, highs, lows, closes, _, volume = generate_fake_candlestick_data(
            start_date="2024-01-01",
            interval="daily",
            length=50,
            gap_types=[],
        )

        with self.Test_plot:
            self.backdrop_candles = PlotCandleStick(
                self.C,
                dates=dates,
                opens=opens,
                closes=closes,
                lows=lows,
                highs=highs,
                volumes=volume,
                label="Backdrop Candles",
                weight=0.2,
                time_formatter="auto",
            )

        self._backdrop_dates = dates
        self._backdrop_lows = lows
        self._backdrop_highs = highs
        self._add_interactive_probe()

        self.Test_plot.X1.fit()
        self.Test_plot.Y1.fit()

    def _add_interactive_probe(self) -> None:
        left_index = 10
        right_index = 16
        low_price = float(min(self._backdrop_lows))
        high_price = float(max(self._backdrop_highs))
        price_span = high_price - low_price
        bottom = low_price + price_span * 0.20
        top = low_price + price_span * 0.35
        self._min_probe_width = float(self._backdrop_dates[2] - self._backdrop_dates[0])
        self._min_probe_height = price_span * 0.08

        probe_p1 = [float(self._backdrop_dates[left_index]), bottom]
        probe_p2 = [float(self._backdrop_dates[right_index]), top]

        with self.Test_plot:
            self.probe_layer = dcg.DrawInPlot(self.C)

        self.probe_box = MovableResizableBoxIndicator(
            self.C,
            layer=self.probe_layer,
            status=self.overlay_status,
            p1=probe_p1,
            p2=probe_p2,
            label="Movable range box indicator",
            min_width=self._min_probe_width,
            min_height=self._min_probe_height,
            allow_inversion=True,
        )

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
    app = TA_Demo(white_theme=False)
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
