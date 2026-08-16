import numpy as np
import pytest

import dearcygui as dcg

from dearcyfi import DearCyFi, InteractiveTool, RangeBoxGeometry, ToolAnchor


class FakeTool(InteractiveTool):
    def __init__(self, tool_id: str) -> None:
        self._tool_id = tool_id
        self.refresh_count = 0
        self.dispose_count = 0

    @property
    def tool_id(self) -> str:
        return self._tool_id

    @property
    def tool_kind(self) -> str:
        return "fake"

    def refresh_projection(self) -> None:
        self.refresh_count += 1

    def dispose(self) -> None:
        self.dispose_count += 1


@pytest.fixture
def context():
    return dcg.Context()


@pytest.fixture
def chart(context):
    return DearCyFi(context, prewarm=False, use_local_time=False)


def _load_chart_candles(chart: DearCyFi) -> None:
    chart.set_data(
        dates=[0.0, 10.0, 20.0, 100.0, 110.0],
        opens=[10.0, 8.0, 7.0, 5.0, 9.0],
        highs=[12.0, 9.0, 8.0, 7.0, 10.0],
        lows=[9.0, 5.0, 6.0, 4.0, 8.0],
        closes=[11.0, 6.0, 7.0, 6.0, 8.0],
        volume=[1.0, 1.0, 1.0, 1.0, 1.0],
    )


def test_anchor_and_geometry_validate_and_normalize():
    anchor = ToolAnchor(10.0, 20.0)
    geometry = RangeBoxGeometry(left_time=30.0, bottom=5.0, right_time=10.0, top=1.0)

    assert anchor.source_time == 10.0
    assert anchor.y_value == 20.0
    assert geometry.left_time == 10.0
    assert geometry.right_time == 30.0
    assert geometry.bottom == 1.0
    assert geometry.top == 5.0
    assert geometry.get_anchor("top_left") == ToolAnchor(10.0, 5.0)

    with pytest.raises(ValueError, match="finite"):
        ToolAnchor(np.nan, 1.0)
    with pytest.raises(ValueError, match="finite"):
        RangeBoxGeometry(left_time=0.0, bottom=1.0, right_time=np.inf, top=2.0)


def test_register_tool_rejects_duplicate_identity(chart):
    tool = FakeTool("alpha")
    chart.register_tool(tool)

    with pytest.raises(ValueError, match="already registered"):
        chart.register_tool(FakeTool("alpha"))

    assert chart.tools == (tool,)


def test_add_box_requires_candles(chart):
    with pytest.raises(RuntimeError, match="before candles are loaded"):
        chart.add_box()


def test_add_box_default_and_explicit_geometry(chart):
    _load_chart_candles(chart)
    chart.X1.min = 0.0
    chart.X1.max = 100.0
    chart.Y1.min = 0.0
    chart.Y1.max = 10.0

    default_box = chart.add_box()
    explicit_box = chart.add_box(left_time=15.0, bottom=5.5, right_time=30.0, top=8.5)

    assert len(chart.tools) == 2
    assert chart.boxes == (default_box, explicit_box)
    assert default_box.tool_id == "range-box-1"
    assert default_box.source_geometry == RangeBoxGeometry(40.0, 4.0, 60.0, 6.0)
    assert default_box._layer.parent is chart
    assert explicit_box.source_geometry == RangeBoxGeometry(15.0, 5.5, 30.0, 8.5)


def test_move_resize_programmatic_mutation_and_callbacks(chart):
    _load_chart_candles(chart)
    changes = []
    commits = []
    box = chart.add_box(
        left_time=10.0,
        bottom=5.0,
        right_time=20.0,
        top=10.0,
        on_geometry_changing=lambda tool, geometry: changes.append((tool.tool_id, geometry)),
        on_geometry_committed=lambda tool, geometry: commits.append((tool.tool_id, geometry)),
    )

    box._handle_dragging("move", (5.0, 2.0))
    box._handle_dragged("move", (5.0, 2.0))

    assert box.source_geometry == RangeBoxGeometry(15.0, 7.0, 25.0, 12.0)
    assert changes[-1][1] == RangeBoxGeometry(15.0, 7.0, 25.0, 12.0)
    assert commits[-1][1] == RangeBoxGeometry(15.0, 7.0, 25.0, 12.0)

    box._handle_dragging("top_right", (4.0, 3.0))
    box._handle_dragged("top_right", (4.0, 3.0))

    assert box.get_anchor("bottom_left") == ToolAnchor(15.0, 7.0)
    assert box.get_anchor("top_right") == ToolAnchor(29.0, 15.0)

    box.set_geometry(RangeBoxGeometry(30.0, 8.0, 40.0, 12.0))
    assert commits[-1][1] == RangeBoxGeometry(30.0, 8.0, 40.0, 12.0)


def test_corner_drag_can_invert_through_opposite_corner_without_error(chart):
    _load_chart_candles(chart)
    box = chart.add_box(
        left_time=10.0,
        bottom=5.0,
        right_time=20.0,
        top=10.0,
        min_source_width=1.0,
        min_source_height=0.5,
    )

    box._handle_dragging("top_left", (15.0, -8.0))

    assert box.source_geometry == RangeBoxGeometry(20.0, 2.0, 25.0, 5.0)
    assert box._active_role == "bottom_right"

    box._handle_dragged("top_left", (15.0, -8.0))

    assert box.source_geometry == RangeBoxGeometry(20.0, 2.0, 25.0, 5.0)


def test_remove_all_boxes_is_idempotent_and_preserves_other_tools(chart):
    _load_chart_candles(chart)
    other_tool = FakeTool("fake-1")
    chart.register_tool(other_tool)
    chart.add_box(left_time=10.0, bottom=5.0, right_time=20.0, top=10.0)
    chart.add_box(left_time=30.0, bottom=6.0, right_time=40.0, top=11.0)

    chart.remove_all_boxes()
    chart.remove_all_boxes()

    assert chart.boxes == ()
    assert chart.tools == (other_tool,)


def test_print_boxes_and_snapshots_include_empty_and_non_empty_state(chart):
    _load_chart_candles(chart)

    assert chart.print_boxes() == "No range boxes."

    box = chart.add_box(left_time=10.0, bottom=5.0, right_time=20.0, top=10.0)
    output = chart.print_boxes()
    snapshots = chart.get_box_snapshots()

    assert box.tool_id in output
    assert "source:" in output
    assert "plot:" in output
    assert len(snapshots) == 1
    assert snapshots[0].tool_id == box.tool_id


def test_collapse_restore_and_reload_refresh_boxes(chart):
    _load_chart_candles(chart)
    box = chart.add_box(left_time=10.0, bottom=5.0, right_time=100.0, top=10.0)
    uncollapsed_plot_geometry = box.plot_geometry

    chart.collapse_time_chart(debug=False)
    collapsed_plot_geometry = box.plot_geometry

    assert box.source_geometry == RangeBoxGeometry(10.0, 5.0, 100.0, 10.0)
    assert collapsed_plot_geometry.left_time == 10.0
    assert collapsed_plot_geometry.right_time == 30.0

    chart.restore_time_chart()
    assert box.plot_geometry == uncollapsed_plot_geometry

    previous_candle = box.get_current_candle_series()
    chart.set_data(
        dates=[0.0, 10.0, 20.0, 30.0],
        opens=[1.0, 2.0, 3.0, 4.0],
        highs=[2.0, 3.0, 4.0, 5.0],
        lows=[0.0, 1.0, 2.0, 3.0],
        closes=[1.5, 2.5, 3.5, 4.5],
        volume=[1.0, 1.0, 1.0, 1.0],
    )

    assert box.source_geometry == RangeBoxGeometry(10.0, 5.0, 100.0, 10.0)
    assert box.get_current_candle_series() is chart.candlestick_plot
    assert box.get_current_candle_series() is previous_candle


def test_generic_tool_refreshes_on_collapse_restore_and_data_replace(chart):
    _load_chart_candles(chart)
    fake = FakeTool("observer")
    chart.register_tool(fake)

    chart.collapse_time_chart(debug=False)
    chart.restore_time_chart()
    chart.set_data(
        dates=[0.0, 10.0, 20.0],
        opens=[1.0, 2.0, 3.0],
        highs=[2.0, 3.0, 4.0],
        lows=[0.0, 1.0, 2.0],
        closes=[1.5, 2.5, 3.5],
    )

    assert fake.refresh_count >= 3


def test_anchor_tooltip_coordinator_handles_switching_and_stale_leave(chart):
    _load_chart_candles(chart)
    chart.cursor_tag_formatter = lambda timestamp: f"ts={timestamp:.1f}"
    box = chart.add_box(left_time=10.0, bottom=5.0, right_time=20.0, top=10.0)
    top_left_target = box._anchor_buttons["top_left"]
    bottom_right_target = box._anchor_buttons["bottom_right"]

    chart._anchor_tooltip_coordinator.activate(box, "top_left", top_left_target)
    first_tooltip = chart._anchor_tooltip_coordinator._tooltip
    assert chart._anchor_tooltip_coordinator._resolve_tooltip_parent(top_left_target) is top_left_target.parent
    assert chart._anchor_tooltip_coordinator._tool_text.value == f"Tool: {box.tool_id}"
    assert chart._anchor_tooltip_coordinator._anchor_text.value == "Anchor: top_left"
    assert chart._anchor_tooltip_coordinator._date_text.value == "Date: ts=10.0"
    assert chart._anchor_tooltip_coordinator._price_text.value == "Price: 10.0000"

    chart._anchor_tooltip_coordinator.activate(box, "top_left", top_left_target)
    assert chart._anchor_tooltip_coordinator._tooltip is first_tooltip

    chart._anchor_tooltip_coordinator.activate(box, "bottom_right", bottom_right_target)
    assert chart._anchor_tooltip_coordinator._tooltip is not first_tooltip
    assert chart._anchor_tooltip_coordinator._anchor_text.value == "Anchor: bottom_right"

    chart._anchor_tooltip_coordinator.handle_lost_hover(top_left_target)
    assert chart._anchor_tooltip_coordinator._tooltip is not None

    box._handle_dragging("bottom_right", (5.0, 2.0))
    assert chart._anchor_tooltip_coordinator._date_text.value == "Date: ts=25.0"
    assert chart._anchor_tooltip_coordinator._price_text.value == "Price: 7.0000"
    box._handle_dragged("bottom_right", (5.0, 2.0))

    chart.anchor_tooltips_enabled = False
    chart._anchor_tooltip_coordinator.activate(box, "top_left", top_left_target)
    assert chart._anchor_tooltip_coordinator._tooltip is None

    chart.anchor_tooltips_enabled = True
    chart._anchor_tooltip_coordinator.activate(box, "top_left", top_left_target)
    assert chart._anchor_tooltip_coordinator._tooltip is not None
    chart.remove_all_boxes()
    assert chart._anchor_tooltip_coordinator._tooltip is None