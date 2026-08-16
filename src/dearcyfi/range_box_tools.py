from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

import dearcygui as dcg
import numpy as np

if TYPE_CHECKING:
    from .core import DearCyFi


_SUPPORTED_Y_AXES = (dcg.Axis.Y1, dcg.Axis.Y2, dcg.Axis.Y3)
_BOX_TOOL_KIND = "range-box"
_ANCHOR_ROLE_ORDER = ("top_left", "top_right", "bottom_left", "bottom_right")
_OPPOSITE_ANCHOR_ROLE = {
    "top_left": "bottom_right",
    "top_right": "bottom_left",
    "bottom_left": "top_right",
    "bottom_right": "top_left",
}


def _finite_float(value: float, *, name: str) -> float:
    numeric = float(value)
    if not np.isfinite(numeric):
        raise ValueError(f"{name} must be finite")
    return numeric


def _validate_y_axis(y_axis: dcg.Axis) -> dcg.Axis:
    if y_axis not in _SUPPORTED_Y_AXES:
        raise ValueError("y_axis must be dcg.Axis.Y1, dcg.Axis.Y2, or dcg.Axis.Y3")
    return y_axis


@dataclass(frozen=True)
class ToolAnchor:
    source_time: float
    y_value: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_time", _finite_float(self.source_time, name="source_time"))
        object.__setattr__(self, "y_value", _finite_float(self.y_value, name="y_value"))


@dataclass(frozen=True)
class RangeBoxGeometry:
    left_time: float
    bottom: float
    right_time: float
    top: float

    def __post_init__(self) -> None:
        left_time = _finite_float(self.left_time, name="left_time")
        bottom = _finite_float(self.bottom, name="bottom")
        right_time = _finite_float(self.right_time, name="right_time")
        top = _finite_float(self.top, name="top")
        if left_time > right_time:
            left_time, right_time = right_time, left_time
        if bottom > top:
            bottom, top = top, bottom
        object.__setattr__(self, "left_time", left_time)
        object.__setattr__(self, "bottom", bottom)
        object.__setattr__(self, "right_time", right_time)
        object.__setattr__(self, "top", top)

    @property
    def width(self) -> float:
        return float(self.right_time - self.left_time)

    @property
    def height(self) -> float:
        return float(self.top - self.bottom)

    def get_anchor(self, role: str) -> ToolAnchor:
        if role == "top_left":
            return ToolAnchor(self.left_time, self.top)
        if role == "top_right":
            return ToolAnchor(self.right_time, self.top)
        if role == "bottom_left":
            return ToolAnchor(self.left_time, self.bottom)
        if role == "bottom_right":
            return ToolAnchor(self.right_time, self.bottom)
        raise KeyError(f"Unknown anchor role: {role!r}")


@dataclass(frozen=True)
class RangeBoxDiagnosticSnapshot:
    tool_id: str
    tool_kind: str
    y_axis: dcg.Axis
    source_geometry: RangeBoxGeometry
    plot_geometry: RangeBoxGeometry


class InteractiveTool(ABC):
    @property
    @abstractmethod
    def tool_id(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def tool_kind(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def refresh_projection(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def dispose(self) -> None:
        raise NotImplementedError


class AnchorTooltipCoordinator:
    def __init__(self, chart: DearCyFi) -> None:
        self._chart = chart
        self._active_tool: RangeBoxTool | None = None
        self._active_role: str | None = None
        self._active_target = None
        self._tooltip = None
        self._tool_text = None
        self._anchor_text = None
        self._date_text = None
        self._price_text = None

    def clear(self) -> None:
        if self._tooltip is not None:
            try:
                self._tooltip.delete_item()
            except Exception:
                pass
        self._active_tool = None
        self._active_role = None
        self._active_target = None
        self._tooltip = None
        self._tool_text = None
        self._anchor_text = None
        self._date_text = None
        self._price_text = None

    def activate(self, tool: RangeBoxTool, role: str, target) -> None:
        if not self._chart.anchor_tooltips_enabled or not tool.anchor_tooltips_enabled:
            return
        if target is self._active_target and self._tooltip is not None:
            self._active_tool = tool
            self._active_role = role
            self._update_rows()
            return
        self.clear()
        with dcg.Tooltip(
            self._chart.context,
            target=target,
            parent=self._resolve_tooltip_parent(target),
        ) as tooltip:
            self._tool_text = dcg.Text(self._chart.context, value="")
            self._anchor_text = dcg.Text(self._chart.context, value="")
            self._date_text = dcg.Text(self._chart.context, value="")
            self._price_text = dcg.Text(self._chart.context, value="")
        self._tooltip = tooltip
        self._active_tool = tool
        self._active_role = role
        self._active_target = target
        self._update_rows()

    def handle_lost_hover(self, target) -> None:
        if target is self._active_target:
            self.clear()

    def clear_for_tool(self, tool: RangeBoxTool) -> None:
        if tool is self._active_tool:
            self.clear()

    def refresh_for_tool(self, tool: RangeBoxTool) -> None:
        if tool is self._active_tool and self._tooltip is not None:
            self._update_rows()

    def _update_rows(self) -> None:
        if self._active_tool is None or self._active_role is None:
            return
        anchor = self._active_tool.get_anchor(self._active_role)
        self._tool_text.value = f"Tool: {self._active_tool.tool_id}"
        self._anchor_text.value = f"Anchor: {self._active_role}"
        self._date_text.value = f"Date: {self._chart.format_cursor_timestamp(anchor.source_time)}"
        self._price_text.value = f"Price: {anchor.y_value:,.4f}"
        try:
            self._chart.context.viewport.wake(full_refresh=True)
        except Exception:
            pass

    def _resolve_tooltip_parent(self, target):
        chart_parent = getattr(self._chart, "parent", None)
        if chart_parent is not None:
            return chart_parent
        target_parent = getattr(target, "parent", None)
        if target_parent is not None:
            return target_parent
        raise RuntimeError("Could not resolve a tooltip parent for range-box anchors")


def _box_geometry_from_values(
    left_time: float,
    bottom: float,
    right_time: float,
    top: float,
) -> RangeBoxGeometry:
    return RangeBoxGeometry(left_time=float(left_time), bottom=float(bottom), right_time=float(right_time), top=float(top))


class RangeBoxTool(InteractiveTool):
    def __init__(
        self,
        chart: DearCyFi,
        *,
        tool_id: str,
        geometry: RangeBoxGeometry,
        y_axis: dcg.Axis = dcg.Axis.Y1,
        on_geometry_changing: Callable[[RangeBoxTool, RangeBoxGeometry], None] | None = None,
        on_geometry_committed: Callable[[RangeBoxTool, RangeBoxGeometry], None] | None = None,
        anchor_tooltips_enabled: bool = True,
        hit_size: float = 18.0,
        min_source_width: float = 1.0,
        min_source_height: float = 0.01,
        line_color=(50, 140, 255, 255),
        hover_line_color=(255, 170, 60, 255),
        active_line_color=(255, 210, 120, 255),
        fill_color=(50, 140, 255, 80),
        hover_fill_color=(255, 170, 60, 110),
        active_fill_color=(255, 190, 80, 125),
    ) -> None:
        if not isinstance(tool_id, str) or not tool_id:
            raise ValueError("tool_id must be a non-empty string")
        self._chart = chart
        self._context = chart.context
        self._tool_id = tool_id
        self._tool_kind = _BOX_TOOL_KIND
        self._y_axis = _validate_y_axis(y_axis)
        self._on_geometry_changing = on_geometry_changing
        self._on_geometry_committed = on_geometry_committed
        self._anchor_tooltips_enabled = bool(anchor_tooltips_enabled)
        self._hit_size = _finite_float(hit_size, name="hit_size")
        self._min_source_width = _finite_float(min_source_width, name="min_source_width")
        self._min_source_height = _finite_float(min_source_height, name="min_source_height")
        self._line_color = dcg.color_as_int(line_color)
        self._hover_line_color = dcg.color_as_int(hover_line_color)
        self._active_line_color = dcg.color_as_int(active_line_color)
        self._fill_color = dcg.color_as_int(fill_color)
        self._hover_fill_color = dcg.color_as_int(hover_fill_color)
        self._active_fill_color = dcg.color_as_int(active_fill_color)
        self._source_geometry = self._validate_geometry(geometry)
        self._plot_geometry = self._source_geometry
        self._active_role: str | None = None
        self._drag_origin_role: str | None = None
        self._hover_role: str | None = None
        self._was_dragging = False
        self._drag_backup_plot_geometry = self._source_geometry
        self._drag_backup_source_geometry = self._source_geometry
        self._disposed = False

        with self._chart:
            self._layer = dcg.DrawInPlot(self._context, axes=(dcg.Axis.X1, self._y_axis))
            with self._layer:
                self._rect = dcg.DrawRect(
                    self._context,
                    pmin=(0.0, 0.0),
                    pmax=(0.0, 0.0),
                    color=self._line_color,
                    fill=self._fill_color,
                    thickness=2,
                )
                self._body_button = dcg.DrawInvisibleButton(
                    self._context,
                    p1=(0.0, 0.0),
                    p2=(0.0, 0.0),
                    button=dcg.MouseButtonMask.ANY,
                    capture_mouse=True,
                    min_side=max(4.0, self._hit_size * 0.75),
                )
                self._anchor_buttons = {
                    role: dcg.DrawInvisibleButton(
                        self._context,
                        p1=(0.0, 0.0),
                        p2=(0.0, 0.0),
                        button=dcg.MouseButtonMask.ANY,
                        capture_mouse=True,
                        min_side=self._hit_size,
                    )
                    for role in _ANCHOR_ROLE_ORDER
                }

        self._body_button.handlers = self._build_handlers("move", dcg.MouseCursor.RESIZE_ALL, is_anchor=False)
        for role, button in self._anchor_buttons.items():
            button.handlers = self._build_handlers(role, self._cursor_for_role(role), is_anchor=True)
        self.refresh_projection()

    @property
    def tool_id(self) -> str:
        return self._tool_id

    @property
    def tool_kind(self) -> str:
        return self._tool_kind

    @property
    def y_axis(self) -> dcg.Axis:
        return self._y_axis

    @property
    def anchor_roles(self) -> tuple[str, ...]:
        return _ANCHOR_ROLE_ORDER

    @property
    def anchor_tooltips_enabled(self) -> bool:
        return self._anchor_tooltips_enabled

    @anchor_tooltips_enabled.setter
    def anchor_tooltips_enabled(self, value: bool) -> None:
        self._anchor_tooltips_enabled = bool(value)
        if not self._anchor_tooltips_enabled:
            self._chart._anchor_tooltip_coordinator.clear_for_tool(self)

    @property
    def source_geometry(self) -> RangeBoxGeometry:
        return self._source_geometry

    @property
    def plot_geometry(self) -> RangeBoxGeometry:
        return self._plot_geometry

    @property
    def disposed(self) -> bool:
        return self._disposed

    def get_anchor(self, role: str) -> ToolAnchor:
        return self._source_geometry.get_anchor(role)

    def get_plot_anchor(self, role: str) -> ToolAnchor:
        anchor = self._plot_geometry.get_anchor(role)
        return ToolAnchor(anchor.source_time, anchor.y_value)

    def get_current_candle_series(self):
        if self._chart.candlestick_plot is None:
            raise RuntimeError("Range box requires candles to be loaded")
        return self._chart.candlestick_plot

    def refresh_projection(self) -> None:
        if self._disposed:
            return
        self._plot_geometry = self._project_geometry(self._source_geometry)
        self._sync_draw_items()
        self._chart._anchor_tooltip_coordinator.refresh_for_tool(self)

    def set_geometry(self, geometry: RangeBoxGeometry) -> None:
        validated = self._validate_geometry(geometry)
        self._source_geometry = validated
        self._plot_geometry = self._project_geometry(validated)
        self._sync_draw_items()
        self._emit_geometry_committed(validated)

    def dispose(self) -> None:
        if self._disposed:
            return
        self._chart._anchor_tooltip_coordinator.clear_for_tool(self)
        try:
            self._layer.delete_item()
        except Exception:
            pass
        self._disposed = True

    def diagnostic_snapshot(self) -> RangeBoxDiagnosticSnapshot:
        return RangeBoxDiagnosticSnapshot(
            tool_id=self.tool_id,
            tool_kind=self.tool_kind,
            y_axis=self.y_axis,
            source_geometry=self.source_geometry,
            plot_geometry=self.plot_geometry,
        )

    def _build_handlers(self, role: str, cursor, *, is_anchor: bool) -> list:
        cursor_on_hover = dcg.ConditionalHandler(self._context)
        with cursor_on_hover:
            dcg.MouseCursorHandler(self._context, cursor=cursor)
            dcg.HoverHandler(self._context)

        return [
            dcg.GotHoverHandler(self._context, callback=lambda _sender, target: self._handle_hover_enter(role, is_anchor, target)),
            dcg.LostHoverHandler(self._context, callback=lambda _sender, target: self._handle_hover_leave(role, is_anchor, target)),
            dcg.DraggingHandler(self._context, callback=lambda _sender, _target, delta: self._handle_dragging(role, delta)),
            dcg.DraggedHandler(self._context, callback=lambda _sender, _target, delta: self._handle_dragged(role, delta)),
            cursor_on_hover,
        ]

    @staticmethod
    def _cursor_for_role(role: str):
        if role in {"top_left", "bottom_right"}:
            return dcg.MouseCursor.RESIZE_NWSE
        return dcg.MouseCursor.RESIZE_NESW

    def _handle_hover_enter(self, role: str, is_anchor: bool, target) -> None:
        if not self._was_dragging:
            self._hover_role = role
        self._apply_visual_state()
        if is_anchor:
            self._chart._anchor_tooltip_coordinator.activate(self, role, target)
        self._wake_viewport()

    def _handle_hover_leave(self, role: str, is_anchor: bool, target) -> None:
        if self._was_dragging and role == self._drag_origin_role:
            return
        if self._hover_role == role:
            self._hover_role = None
        if is_anchor:
            self._chart._anchor_tooltip_coordinator.handle_lost_hover(target)
        self._apply_visual_state()
        self._wake_viewport()

    def _handle_dragging(self, role: str, delta) -> None:
        if not self._was_dragging or self._drag_origin_role != role:
            self._drag_backup_plot_geometry = self._plot_geometry
            self._drag_backup_source_geometry = self._source_geometry
            self._drag_origin_role = role
            self._active_role = role
            self._hover_role = role
            self._was_dragging = True
        updated_geometry = self._geometry_from_plot_delta(role, delta)
        self._source_geometry = updated_geometry
        self._plot_geometry = self._project_geometry(updated_geometry)
        self._sync_draw_items()
        self._emit_geometry_changing(updated_geometry)

    def _handle_dragged(self, role: str, delta) -> None:
        if self._was_dragging and self._drag_origin_role == role:
            updated_geometry = self._geometry_from_plot_delta(role, delta)
            self._source_geometry = updated_geometry
            self._plot_geometry = self._project_geometry(updated_geometry)
            self._sync_draw_items()
            self._emit_geometry_committed(updated_geometry)
        self._was_dragging = False
        self._drag_origin_role = None
        self._active_role = None
        self._hover_role = self._hover_role if self._hover_role is not None else role
        self._apply_visual_state()
        self._wake_viewport()

    def _geometry_from_plot_delta(self, role: str, delta) -> RangeBoxGeometry:
        dx = _finite_float(float(delta[0]), name="drag delta x")
        dy = _finite_float(float(delta[1]), name="drag delta y")
        start = self._drag_backup_plot_geometry

        if role == "move":
            proposed_plot = _box_geometry_from_values(
                start.left_time + dx,
                start.bottom + dy,
                start.right_time + dx,
                start.top + dy,
            )
            source_geometry = self._source_geometry_from_plot(proposed_plot)
            return self._validate_geometry(source_geometry)

        return self._corner_geometry_from_plot_delta(role, dx, dy)
        raise KeyError(f"Unknown drag role: {role!r}")

    def _corner_geometry_from_plot_delta(self, role: str, dx: float, dy: float) -> RangeBoxGeometry:
        start_plot_anchor = self._drag_backup_plot_geometry.get_anchor(role)
        fixed_source_anchor = self._drag_backup_source_geometry.get_anchor(_OPPOSITE_ANCHOR_ROLE[role])

        dragged_source_time = self._expand_plot_x(start_plot_anchor.source_time + dx)
        dragged_y_value = float(start_plot_anchor.y_value + dy)

        dragged_on_left = dragged_source_time <= fixed_source_anchor.source_time
        dragged_on_top = dragged_y_value >= fixed_source_anchor.y_value

        if abs(dragged_source_time - fixed_source_anchor.source_time) < self._min_source_width:
            dragged_source_time = (
                fixed_source_anchor.source_time - self._min_source_width
                if dragged_on_left
                else fixed_source_anchor.source_time + self._min_source_width
            )
        if abs(dragged_y_value - fixed_source_anchor.y_value) < self._min_source_height:
            dragged_y_value = (
                fixed_source_anchor.y_value + self._min_source_height
                if dragged_on_top
                else fixed_source_anchor.y_value - self._min_source_height
            )

        self._active_role = self._resolve_dragged_role(
            dragged_source_time,
            dragged_y_value,
            fixed_source_anchor,
        )
        self._hover_role = self._active_role
        return self._validate_geometry(
            _box_geometry_from_values(
                dragged_source_time,
                dragged_y_value,
                fixed_source_anchor.source_time,
                fixed_source_anchor.y_value,
            )
        )

    @staticmethod
    def _resolve_dragged_role(
        dragged_source_time: float,
        dragged_y_value: float,
        fixed_anchor: ToolAnchor,
    ) -> str:
        horizontal = "left" if dragged_source_time <= fixed_anchor.source_time else "right"
        vertical = "top" if dragged_y_value >= fixed_anchor.y_value else "bottom"
        return f"{vertical}_{horizontal}"

    def _source_geometry_from_plot(self, geometry: RangeBoxGeometry) -> RangeBoxGeometry:
        return _box_geometry_from_values(
            self._expand_plot_x(geometry.left_time),
            geometry.bottom,
            self._expand_plot_x(geometry.right_time),
            geometry.top,
        )

    def _project_geometry(self, geometry: RangeBoxGeometry) -> RangeBoxGeometry:
        return _box_geometry_from_values(
            self._project_source_x(geometry.left_time),
            geometry.bottom,
            self._project_source_x(geometry.right_time),
            geometry.top,
        )

    def _project_source_x(self, source_time: float) -> float:
        time_map = self._chart._gap_manager.time_map
        if self._chart._gap_manager.time_is_collapsed and time_map is not None:
            return float(time_map.project(float(source_time), in_gap="next"))
        return float(source_time)

    def _expand_plot_x(self, plot_x: float) -> float:
        return float(self._chart.expand_cursor_plot_x_to_real_time(plot_x))

    def _validate_geometry(self, geometry: RangeBoxGeometry) -> RangeBoxGeometry:
        normalized = RangeBoxGeometry(
            left_time=geometry.left_time,
            bottom=geometry.bottom,
            right_time=geometry.right_time,
            top=geometry.top,
        )
        if normalized.width < self._min_source_width:
            raise ValueError(
                f"Range box width must be at least {self._min_source_width:g} source-time units"
            )
        if normalized.height < self._min_source_height:
            raise ValueError(
                f"Range box height must be at least {self._min_source_height:g} price units"
            )
        return normalized

    def _sync_draw_items(self) -> None:
        geometry = self._plot_geometry
        self._rect.pmin = (geometry.left_time, geometry.bottom)
        self._rect.pmax = (geometry.right_time, geometry.top)

        width = max(geometry.width, 0.0)
        height = max(geometry.height, 0.0)
        pad_x = min(width * 0.25, max(width * 0.12, 0.0))
        pad_y = min(height * 0.25, max(height * 0.12, 0.0))
        self._body_button.p1 = (geometry.left_time + pad_x, geometry.bottom + pad_y)
        self._body_button.p2 = (geometry.right_time - pad_x, geometry.top - pad_y)

        for role, button in self._anchor_buttons.items():
            anchor = geometry.get_anchor(role)
            button.p1 = (anchor.source_time, anchor.y_value)
            button.p2 = (anchor.source_time, anchor.y_value)
        self._apply_visual_state()
        self._wake_viewport()

    def _apply_visual_state(self) -> None:
        if self._active_role is not None:
            self._rect.color = self._active_line_color
            self._rect.fill = self._active_fill_color
            return
        if self._hover_role is not None:
            self._rect.color = self._hover_line_color
            self._rect.fill = self._hover_fill_color
            return
        self._rect.color = self._line_color
        self._rect.fill = self._fill_color

    def _emit_geometry_changing(self, geometry: RangeBoxGeometry) -> None:
        if callable(self._on_geometry_changing):
            self._on_geometry_changing(self, geometry)
        self._chart._anchor_tooltip_coordinator.refresh_for_tool(self)
        self._wake_viewport()

    def _emit_geometry_committed(self, geometry: RangeBoxGeometry) -> None:
        if callable(self._on_geometry_committed):
            self._on_geometry_committed(self, geometry)
        self._chart._anchor_tooltip_coordinator.refresh_for_tool(self)
        self._wake_viewport()

    def _wake_viewport(self) -> None:
        try:
            self._context.viewport.wake(full_refresh=True)
        except Exception:
            pass