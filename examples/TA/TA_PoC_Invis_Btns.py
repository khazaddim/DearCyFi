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


class PlotLogicalHitRegion:
    def __init__(self, context, *, plot, auto_install: bool = True):
        self.C = context
        self.plot = plot
        self.enabled = True
        self.hovered = False
        self.dragging = False
        self.inside = False
        self.mouse_x = 0.0
        self.mouse_y = 0.0
        self.last_mouse_x = 0.0
        self.last_mouse_y = 0.0
        self.drag_start_x = 0.0
        self.drag_start_y = 0.0
        self.drag_dx = 0.0
        self.drag_dy = 0.0
        self._drag_armed = False
        self._drag_armed_x = 0.0
        self._drag_armed_y = 0.0
        self._handlers = []

        if auto_install:
            self.install_handlers()

    def contains(self, x_coord: float, y_coord: float) -> bool:
        return False

    def install_handlers(self) -> None:
        if self._handlers:
            return

        self._handlers = [
            dcg.MouseMoveHandler(self.C, callback=self._handle_mouse_move),
            dcg.ClickedHandler(self.C, callback=self._handle_click),
            dcg.DraggingHandler(self.C, callback=self._handle_dragging),
            dcg.DraggedHandler(self.C, callback=self._handle_dragged),
        ]
        self.plot.handlers += self._handlers

    def remove_handlers(self) -> None:
        if not self._handlers:
            return

        self.plot.handlers = [handler for handler in self.plot.handlers if handler not in self._handlers]
        self._handlers = []

    def _update_mouse_state(self) -> None:
        self.last_mouse_x = self.mouse_x
        self.last_mouse_y = self.mouse_y
        self.mouse_x = float(self.plot.X1.mouse_coord)
        self.mouse_y = float(self.plot.Y1.mouse_coord)
        self.inside = self.contains(self.mouse_x, self.mouse_y)

    def _handle_mouse_move(self, *_args) -> None:
        if not self.enabled:
            return

        self._update_mouse_state()
        if self.inside and not self.hovered:
            self.hovered = True
            self.on_hover_enter()
        elif not self.inside and self.hovered and not self.dragging:
            self.hovered = False
            self.on_hover_leave()

        self.on_mouse_move()

    def _handle_click(self, *_args) -> None:
        if not self.enabled:
            return

        self._update_mouse_state()
        if self.inside:
            self._drag_armed = True
            self._drag_armed_x = self.mouse_x
            self._drag_armed_y = self.mouse_y
            self.on_click()
        else:
            self._drag_armed = False

    def _handle_dragging(self, *_args) -> None:
        if not self.enabled:
            return

        self._update_mouse_state()
        if not self.dragging:
            if not self.inside and not self._drag_armed:
                return
            self.dragging = True
            self.hovered = True
            self.drag_start_x = self._drag_armed_x if self._drag_armed else self.mouse_x
            self.drag_start_y = self._drag_armed_y if self._drag_armed else self.mouse_y
            self.drag_dx = self.mouse_x - self.drag_start_x
            self.drag_dy = self.mouse_y - self.drag_start_y
            self._drag_armed = False
            self.on_drag_start()
            self.on_drag()
            return

        self.drag_dx = self.mouse_x - self.drag_start_x
        self.drag_dy = self.mouse_y - self.drag_start_y
        self.on_drag()

    def _handle_dragged(self, *_args) -> None:
        if not self.dragging:
            return

        self._update_mouse_state()
        self.drag_dx = self.mouse_x - self.drag_start_x
        self.drag_dy = self.mouse_y - self.drag_start_y
        self.dragging = False
        self._drag_armed = False
        self.hovered = self.inside
        self.on_drag_end()
        if not self.hovered:
            self.on_hover_leave()

    def on_hover_enter(self) -> None:
        pass

    def on_hover_leave(self) -> None:
        pass

    def on_mouse_move(self) -> None:
        pass

    def on_click(self) -> None:
        pass

    def on_drag_start(self) -> None:
        pass

    def on_drag(self) -> None:
        pass

    def on_drag_end(self) -> None:
        pass


class PlotOwnedProbeBox(PlotLogicalHitRegion):
    def __init__(self, context, *, plot, layer, status, p1, p2):
        self.p1 = (float(p1[0]), float(p1[1]))
        self.p2 = (float(p2[0]), float(p2[1]))
        self.drag_start_p1 = self.p1
        self.drag_start_p2 = self.p2
        self.active_resize_handle = None
        self.hover_resize_handle = None
        self.status = status
        self.handle_half_width = abs(self.p2[0] - self.p1[0]) * 0.06
        self.handle_half_height = abs(self.p2[1] - self.p1[1]) * 0.18
        self.min_width = abs(self.p2[0] - self.p1[0]) * 0.35
        self.min_height = abs(self.p2[1] - self.p1[1]) * 0.45

        with layer:
            self.rect = dcg.DrawRect(
                context,
                pmin=self.p1,
                pmax=self.p2,
                color=(70, 220, 155, 255),
                fill=(70, 220, 155, 75),
                thickness=2,
            )
            self.label = dcg.DrawText(
                context,
                pos=(self.p1[0], self.p2[1]),
                text="Plot-owned subclass demo",
                color=(255, 255, 255, 255),
                size=14,
            )
            self.handle_rects = {}
            for handle_name in ("tl", "tr", "bl", "br"):
                handle_min, handle_max = self._handle_bounds(handle_name)
                self.handle_rects[handle_name] = dcg.DrawRect(
                    context,
                    pmin=handle_min,
                    pmax=handle_max,
                    color=(255, 255, 255, 255),
                    fill=(20, 20, 20, 220),
                    thickness=1,
                )

        super().__init__(context, plot=plot)

    def contains(self, x_coord: float, y_coord: float) -> bool:
        return self._handle_at(x_coord, y_coord) is not None

    def _box_edges(self) -> tuple[float, float, float, float]:
        left = min(self.p1[0], self.p2[0])
        right = max(self.p1[0], self.p2[0])
        bottom = min(self.p1[1], self.p2[1])
        top = max(self.p1[1], self.p2[1])
        return left, right, bottom, top

    def _handle_center(self, handle_name: str) -> tuple[float, float]:
        left, right, bottom, top = self._box_edges()
        x_coord = left if "l" in handle_name else right
        y_coord = bottom if "b" in handle_name else top
        return x_coord, y_coord

    def _handle_bounds(self, handle_name: str) -> tuple[tuple[float, float], tuple[float, float]]:
        center_x, center_y = self._handle_center(handle_name)
        return (
            (center_x - self.handle_half_width, center_y - self.handle_half_height),
            (center_x + self.handle_half_width, center_y + self.handle_half_height),
        )

    def _handle_at(self, x_coord: float, y_coord: float) -> str | None:
        for handle_name in ("tl", "tr", "bl", "br"):
            handle_min, handle_max = self._handle_bounds(handle_name)
            if handle_min[0] <= x_coord <= handle_max[0] and handle_min[1] <= y_coord <= handle_max[1]:
                return handle_name
        return None

    def update_draw_items(self) -> None:
        self.rect.pmin = self.p1
        self.rect.pmax = self.p2
        self.label.pos = (self.p1[0], self.p2[1])
        self._update_handle_draw_items()

    def _update_handle_draw_items(self) -> None:
        for handle_name, handle_rect in self.handle_rects.items():
            handle_min, handle_max = self._handle_bounds(handle_name)
            handle_rect.pmin = handle_min
            handle_rect.pmax = handle_max
            if handle_name == self.active_resize_handle:
                handle_rect.fill = (255, 190, 80, 255)
            elif handle_name == self.hover_resize_handle:
                handle_rect.fill = (255, 230, 120, 255)
            else:
                handle_rect.fill = (20, 20, 20, 220)

    def _set_hover_handle(self, handle_name: str | None) -> None:
        if self.dragging:
            return
        if handle_name == self.hover_resize_handle:
            return
        self.hover_resize_handle = handle_name
        self._update_handle_draw_items()

    def _set_resized_bounds(self, p1, p2) -> None:
        left = float(min(p1[0], p2[0]))
        right = float(max(p1[0], p2[0]))
        bottom = float(min(p1[1], p2[1]))
        top = float(max(p1[1], p2[1]))
        self.p1 = (left, bottom)
        self.p2 = (right, top)
        self.update_draw_items()

    def on_hover_enter(self) -> None:
        self.hover_resize_handle = self._handle_at(self.mouse_x, self.mouse_y)
        self.rect.fill = (70, 220, 155, 125)
        self.rect.color = (180, 255, 220, 255)
        self._update_handle_draw_items()
        self.status.value = f"Hovering green subclass resize handle: {self.hover_resize_handle}."
        self.C.viewport.wake()

    def on_hover_leave(self) -> None:
        self.hover_resize_handle = None
        self.rect.fill = (70, 220, 155, 75)
        self.rect.color = (70, 220, 155, 255)
        self._update_handle_draw_items()
        self.status.value = "Blue uses invisible buttons. Green uses the plot-owned subclass hit region."
        self.C.viewport.wake()

    def on_mouse_move(self) -> None:
        self._set_hover_handle(self._handle_at(self.mouse_x, self.mouse_y))

    def on_click(self) -> None:
        self.active_resize_handle = self._handle_at(self.mouse_x, self.mouse_y)
        self.hover_resize_handle = self.active_resize_handle
        self._update_handle_draw_items()
        self.status.value = f"Clicked green subclass handle {self.active_resize_handle}: drag to resize."
        self.C.viewport.wake()

    def on_drag_start(self) -> None:
        if self.active_resize_handle is None:
            self.active_resize_handle = self._handle_at(self.mouse_x, self.mouse_y)
        if self.active_resize_handle is None:
            return
        self.drag_start_p1 = self.p1
        self.drag_start_p2 = self.p2
        self.rect.fill = (255, 190, 80, 125)
        self.rect.color = (255, 210, 120, 255)
        self._update_handle_draw_items()
        self.status.value = f"Subclass resize started from {self.active_resize_handle}."
        self.C.viewport.wake()

    def on_drag(self) -> None:
        if self.active_resize_handle is None:
            return

        new_p1 = [self.drag_start_p1[0], self.drag_start_p1[1]]
        new_p2 = [self.drag_start_p2[0], self.drag_start_p2[1]]

        if "l" in self.active_resize_handle:
            new_p1[0] = self.drag_start_p1[0] + self.drag_dx
        if "r" in self.active_resize_handle:
            new_p2[0] = self.drag_start_p2[0] + self.drag_dx
        if "b" in self.active_resize_handle:
            new_p1[1] = self.drag_start_p1[1] + self.drag_dy
        if "t" in self.active_resize_handle:
            new_p2[1] = self.drag_start_p2[1] + self.drag_dy

        if new_p2[0] - new_p1[0] < self.min_width:
            if "l" in self.active_resize_handle:
                new_p1[0] = new_p2[0] - self.min_width
            else:
                new_p2[0] = new_p1[0] + self.min_width
        if new_p2[1] - new_p1[1] < self.min_height:
            if "b" in self.active_resize_handle:
                new_p1[1] = new_p2[1] - self.min_height
            else:
                new_p2[1] = new_p1[1] + self.min_height

        self._set_resized_bounds(new_p1, new_p2)
        self.status.value = (
            f"Subclass resizing {self.active_resize_handle}: left={self.p1[0]:.0f}, right={self.p2[0]:.0f}, "
            f"bottom={self.p1[1]:.2f}, top={self.p2[1]:.2f}"
        )
        self.C.viewport.wake()

    def on_drag_end(self) -> None:
        self.active_resize_handle = None
        self.hover_resize_handle = self._handle_at(self.mouse_x, self.mouse_y)
        self.rect.fill = (70, 220, 155, 125 if self.hovered else 75)
        self.rect.color = (180, 255, 220, 255) if self.hovered else (70, 220, 155, 255)
        self._update_handle_draw_items()
        self.status.value = "Subclass resize released: green square resized without invisible buttons."
        self.C.viewport.wake()


class TA_Demo:
    def __init__(self, white_theme: bool = False):
        self.C = dcg.Context()
        self.C.queue = AsyncPoolExecutor()
        self.C.viewport.wait_for_input = True
        self.drag_origin = None
        self.resize_origin = None
        self.active_resize_handle = None

        if white_theme:
            self.C.viewport.initialize(height=900, width=1600, theme=self._white_theme())
        else:
            self.C.viewport.initialize(height=900, width=1600)

        with dcg.Window(self.C, label="TA Proof of Concept", primary=True, width="fillx", height="filly") as main_window:
            with dcg.VerticalLayout(self.C, width="fillx", height="filly"):
                dcg.Text(
                    self.C,
                    value="Backdrop candles plus invisible-button and plot-owned subclass overlays for TA interaction tests.",
                )
                self.overlay_status = dcg.Text(
                    self.C,
                    value="Blue uses invisible buttons. Green uses the plot-owned subclass hit region.",
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

        self._probe_p1 = [float(self._backdrop_dates[left_index]), bottom]
        self._probe_p2 = [float(self._backdrop_dates[right_index]), top]
        subclass_p1 = [float(self._backdrop_dates[24]), low_price + price_span * 0.52]
        subclass_p2 = [float(self._backdrop_dates[30]), low_price + price_span * 0.67]

        with self.Test_plot:
            self.probe_layer = dcg.DrawInPlot(self.C)

        with self.probe_layer:
            self.probe_rect = dcg.DrawRect(
                self.C,
                pmin=tuple(self._probe_p1),
                pmax=tuple(self._probe_p2),
                color=(50, 140, 255, 255),
                fill=(50, 140, 255, 80),
                thickness=2,
            )
            self.probe_label = dcg.DrawText(
                self.C,
                pos=(self._probe_p1[0], self._probe_p2[1]),
                text="Invisible button demo",
                color=(255, 255, 255, 255),
                size=14,
            )
            self.probe_button = dcg.DrawInvisibleButton(
                self.C,
                p1=tuple(self._probe_p1),
                p2=tuple(self._probe_p2),
                button=dcg.MouseButtonMask.ANY,
                capture_mouse=True,
            )

            self._resize_handles = {}
            self._resize_buttons = {}
            for handle_name in ("tl", "tr", "bl", "br"):
                handle_center = self._handle_center(handle_name)
                self._resize_handles[handle_name] = dcg.DrawRect(
                    self.C,
                    pmin=(handle_center[0], handle_center[1]),
                    pmax=(handle_center[0], handle_center[1]),
                    color=(255, 255, 255, 255),
                    fill=(20, 20, 20, 220),
                    thickness=1,
                )
                self._resize_buttons[handle_name] = dcg.DrawInvisibleButton(
                    self.C,
                    p1=(handle_center[0], handle_center[1]),
                    p2=(handle_center[0], handle_center[1]),
                    min_side=24,
                    button=dcg.MouseButtonMask.ANY,
                    capture_mouse=True,
                )

        self._update_resize_handles()
        self.subclass_probe_box = PlotOwnedProbeBox(
            self.C,
            plot=self.Test_plot,
            layer=self.probe_layer,
            status=self.overlay_status,
            p1=subclass_p1,
            p2=subclass_p2,
        )

        def on_hover_enter(*_args):
            self.probe_rect.fill = (255, 170, 60, 110)
            self.probe_rect.color = (255, 170, 60, 255)
            self.overlay_status.value = "Hover detected: the invisible button is tracking the blue box."
            self.C.viewport.wake()

        def on_hover_exit(*_args):
            self.probe_rect.fill = (50, 140, 255, 80)
            self.probe_rect.color = (50, 140, 255, 255)
            self.overlay_status.value = "Hover the blue box, click it, then drag it around the plot."
            self.C.viewport.wake()

        def on_clicked(*_args):
            self.drag_origin = [self._probe_p1[0], self._probe_p1[1]]
            self.overlay_status.value = "Clicked: drag to move the invisible-button hit area and its visible proxy."
            self.C.viewport.wake()

        def on_dragging(_sender, _target, delta):
            if self.drag_origin is None:
                self.drag_origin = [self._probe_p1[0], self._probe_p1[1]]

            width = self._probe_p2[0] - self._probe_p1[0]
            height = self._probe_p2[1] - self._probe_p1[1]
            new_p1 = [self.drag_origin[0] + delta[0], self.drag_origin[1] + delta[1]]
            new_p2 = [new_p1[0] + width, new_p1[1] + height]
            self._set_probe_bounds(new_p1, new_p2)
            self.overlay_status.value = (
                f"Dragging: left={new_p1[0]:.0f}, right={new_p2[0]:.0f}, "
                f"bottom={new_p1[1]:.2f}, top={new_p2[1]:.2f}"
            )
            self.C.viewport.wake()

        def on_released(*_args):
            self.drag_origin = None
            self.overlay_status.value = "Released: the invisible button stays attached to the moved box."
            self.C.viewport.wake()

        self.probe_button.handlers = [
            dcg.GotHoverHandler(self.C, callback=on_hover_enter),
            dcg.LostHoverHandler(self.C, callback=on_hover_exit),
            dcg.ClickedHandler(self.C, callback=on_clicked),
            dcg.DraggingHandler(self.C, callback=on_dragging),
            dcg.DraggedHandler(self.C, callback=on_released),
        ]

        for handle_name, button in self._resize_buttons.items():
            button.handlers = self._build_resize_handlers(handle_name)

    def _build_resize_handlers(self, handle_name: str):
        def on_hover_enter(*_args):
            self._resize_handles[handle_name].fill = (255, 210, 70, 255)
            self.overlay_status.value = f"Hovering resize handle: {handle_name}. Drag it to resize the box."
            self.C.viewport.wake()

        def on_hover_exit(*_args):
            if self.active_resize_handle != handle_name:
                self._resize_handles[handle_name].fill = (20, 20, 20, 220)
            self.overlay_status.value = "Hover the box body to move it, or drag a corner handle to resize it."
            self.C.viewport.wake()

        def on_clicked(*_args):
            self.active_resize_handle = handle_name
            self.resize_origin = {
                "p1": [self._probe_p1[0], self._probe_p1[1]],
                "p2": [self._probe_p2[0], self._probe_p2[1]],
            }
            self._resize_handles[handle_name].fill = (255, 210, 70, 255)
            self.overlay_status.value = f"Resize started from {handle_name}."
            self.C.viewport.wake()

        def on_dragging(_sender, _target, delta):
            if self.resize_origin is None:
                return

            new_p1 = [self.resize_origin["p1"][0], self.resize_origin["p1"][1]]
            new_p2 = [self.resize_origin["p2"][0], self.resize_origin["p2"][1]]

            if "l" in handle_name:
                new_p1[0] = self.resize_origin["p1"][0] + delta[0]
            if "r" in handle_name:
                new_p2[0] = self.resize_origin["p2"][0] + delta[0]
            if "b" in handle_name:
                new_p1[1] = self.resize_origin["p1"][1] + delta[1]
            if "t" in handle_name:
                new_p2[1] = self.resize_origin["p2"][1] + delta[1]

            if new_p2[0] - new_p1[0] < self._min_probe_width:
                if "l" in handle_name:
                    new_p1[0] = new_p2[0] - self._min_probe_width
                else:
                    new_p2[0] = new_p1[0] + self._min_probe_width

            if new_p2[1] - new_p1[1] < self._min_probe_height:
                if "b" in handle_name:
                    new_p1[1] = new_p2[1] - self._min_probe_height
                else:
                    new_p2[1] = new_p1[1] + self._min_probe_height

            self._set_probe_bounds(new_p1, new_p2)
            self.overlay_status.value = (
                f"Resizing {handle_name}: left={new_p1[0]:.0f}, right={new_p2[0]:.0f}, "
                f"bottom={new_p1[1]:.2f}, top={new_p2[1]:.2f}"
            )
            self.C.viewport.wake()

        def on_released(*_args):
            self.resize_origin = None
            self.active_resize_handle = None
            self._resize_handles[handle_name].fill = (20, 20, 20, 220)
            self.overlay_status.value = "Resize released: drag the body to move, or grab another corner to resize again."
            self.C.viewport.wake()

        return [
            dcg.GotHoverHandler(self.C, callback=on_hover_enter),
            dcg.LostHoverHandler(self.C, callback=on_hover_exit),
            dcg.ClickedHandler(self.C, callback=on_clicked),
            dcg.DraggingHandler(self.C, callback=on_dragging),
            dcg.DraggedHandler(self.C, callback=on_released),
        ]

    def _handle_center(self, handle_name: str) -> tuple[float, float]:
        x = self._probe_p1[0] if "l" in handle_name else self._probe_p2[0]
        y = self._probe_p1[1] if "b" in handle_name else self._probe_p2[1]
        return (x, y)

    def _update_resize_handles(self) -> None:
        handle_half_size = 0.7
        for handle_name, handle_rect in self._resize_handles.items():
            center_x, center_y = self._handle_center(handle_name)
            handle_rect.pmin = (center_x - handle_half_size, center_y - handle_half_size)
            handle_rect.pmax = (center_x + handle_half_size, center_y + handle_half_size)
            self._resize_buttons[handle_name].p1 = (center_x, center_y)
            self._resize_buttons[handle_name].p2 = (center_x, center_y)

    def _set_probe_bounds(self, p1, p2) -> None:
        self._probe_p1 = [float(p1[0]), float(p1[1])]
        self._probe_p2 = [float(p2[0]), float(p2[1])]
        self.probe_rect.pmin = tuple(self._probe_p1)
        self.probe_rect.pmax = tuple(self._probe_p2)
        self.probe_button.p1 = tuple(self._probe_p1)
        self.probe_button.p2 = tuple(self._probe_p2)
        self.probe_label.pos = (self._probe_p1[0], self._probe_p2[1])
        self._update_resize_handles()

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
