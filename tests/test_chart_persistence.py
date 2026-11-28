from copy import deepcopy
from threading import Event
from time import monotonic
from types import SimpleNamespace

import dearcygui as dcg
import numpy as np
import pytest

from dearcyfi import ChartPersistenceError, DearCyFi, PlotEconometricSeries, RangeBoxGeometry
from dearcyfi import _chart_document as codec
from dearcyfi import _chart_menu
from dearcyfi import _chart_state as state


START = 1_700_000_000.0


def chart(context=None, **options):
    return DearCyFi(context or dcg.Context(), prewarm=False, **options)


def populate(plot):
    dates = START + np.array([0, 60, 120, 600], dtype=float)
    plot.set_data(
        dates=dates, opens=[10, 11, 12, 13], highs=[12, 13, 14, 15],
        lows=[9, 10, 11, 12], closes=[11, 12, 13, 14],
        index=[1, "second", None, False], volume=[100, 120, 115, 150],
        volume_kwargs={"label": "Volume", "normalized_max_fraction": 0.4},
    )
    line = PlotEconometricSeries(
        plot.context, parent=plot, dates=START + np.array([30, 300, 600, 900]),
        values=[0.1, np.nan, 0.2, 0.3], y_axis=dcg.Axis.Y3, label="Independent",
        markers=True, line_color=(120, 50, 180, 255), line_thickness=2.5,
    )
    plot.register_time_series("rates", line, in_gap="previous")
    line.enabled = False
    with plot:
        plot.register_tool(state.RangeBoxTool(
            plot, tool_id="range-box-1", geometry=RangeBoxGeometry(START + 60, 10, START + 600, 14),
            y_axis=dcg.Axis.Y2, hit_size=24, min_source_width=20, min_source_height=0.25,
            anchor_tooltips_enabled=False, fill_color=(20, 40, 60, 80),
        ))
    plot.create_indicator(instance_id="fast", period=2, field="close", y_axis=dcg.Axis.Y2)
    plot.create_indicator(instance_id="slow", period=3, field="high", line_color=(10, 20, 30, 255))
    plot.load_horizontal_bars(num_bars=3, value_space="normalized")
    plot.horizontal_bars.show = False
    plot.horizontal_bars.line_colors = [(30, 40, 50, 255)]
    plot.candlestick_plot._volume_bar_series.enabled = False
    plot.Y2.enabled = True
    plot.Y2.label = "Overlays"
    plot.Y2.scale = dcg.AxisScale.LOG10
    plot.Y2.min, plot.Y2.max = 8, 24
    plot.Y3.enabled = False
    plot.Y3.label = "Rates"
    plot.Y3.min, plot.Y3.max = -1, 1
    plot.legend_config.horizontal = True
    return line


def test_round_trip_mixed_streamed_chart_and_empty_replacement(tmp_path):
    source = chart(use_local_time=False, use_24_hour=True, use_iso8601=True)
    line = populate(source)
    source.collapse_time_chart_vec(debug=False)
    source.vectorized_collapse = False
    source.append_candle(timestamp=START + 1200, open=14, high=16, low=13, close=15, volume=165)
    source.X1.min, source.X1.max = START + 140, START + 220
    source.update_last_candle(close=15.5, volume=173)
    source.candlestick_plot.show = False
    source.indicator_manager.get("fast").series.enabled = False
    snapshot = source.capture_chart_state()
    displays = [record["display"] for record in snapshot["series"] + snapshot["indicators"]]
    displays.append(snapshot["series"][0]["display"]["volume"])
    assert all(not {"show", "enabled"}.intersection(display) for display in displays)
    path = tmp_path / "chart.json"
    source.save_chart(path)
    source.update_last_candle(close=16, volume=180)

    notifications = []
    target = chart(on_chart_restored=notifications.append)
    dir_plot = dcg.PlotLine(target.context, parent=target, X=[START], Y=[9])
    target.add_indicator(period=8)
    target.open_chart(path)
    assert target.capture_chart_state() == snapshot
    assert notifications == [target]
    assert dir_plot.parent is target
    assert target.index.tolist() == [1, "second", None, False, START + 1200]
    assert target.closes[-1] == 15.5 and target.volume[-1] == 173
    assert target._gap_manager.time_map.gap_definitions() == [
        [START + 120, START + 600, 60], [START + 600, START + 1200, 60],
    ]
    assert target._gap_manager.active_method == "vectorized" and not target.vectorized_collapse
    assert target._context_menu_items["collapse"].value
    assert target._context_menu_items["source"].value == "Collapse source: candles"
    assert not target.Y3.enabled and (target.Y3.min, target.Y3.max) == (-1, 1)
    assert target.Y2.enabled and target.Y2.scale == dcg.AxisScale.LOG10
    assert (target.X1.min, target.X1.max) == (START + 140, START + 220)
    restored_line = target.get_time_series("rates")
    restored_items = (
        target.candlestick_plot, target.candlestick_plot._volume_bar_series,
        target.horizontal_bars, restored_line, target.indicator_manager.get("fast").series,
    )
    assert all(item.show and item.enabled for item in restored_items)
    np.testing.assert_array_equal(restored_line.source_dates, line.source_dates)
    np.testing.assert_array_equal(restored_line.plot_dates, line.plot_dates)
    assert np.isnan(restored_line.values[1])
    assert snapshot["series"][1]["data"]["values"][1] is None

    box = target.boxes[0]
    assert box.plot_geometry == source.boxes[0].plot_geometry
    assert box.source_geometry == source.boxes[0].source_geometry
    assert box._body_button.parent is box._layer
    box._handle_dragging("move", (2, 1))
    box._handle_dragged("move", (2, 1))
    assert box.source_geometry.bottom == 11
    moved = box.source_geometry
    target.restore_time_chart()
    assert box.plot_geometry == box.source_geometry == moved
    np.testing.assert_array_equal(restored_line.plot_dates, line.source_dates)
    fast = target.indicator_manager.get("fast")
    np.testing.assert_allclose(fast.series.values, [np.nan, 11.5, 12.5, 13.5, 14.75])
    target.edit_indicator("fast", period=3)
    assert fast.series.parameters["period"] == 3
    assert target.indicator_manager.get("slow").calculator.field == "high"
    assert target.create_indicator(period=2).instance_id not in {"fast", "slow"}
    assert target.add_box().tool_id != box.tool_id

    target.restore_chart_state(chart().capture_chart_state())
    assert dir_plot.parent is target
    assert not target.time_series_ids and not target.indicator_ids and not target.tools
    assert target.candlestick_plot is target.horizontal_bars is None
    assert box.disposed and restored_line.parent is None


def test_alternate_collapse_source_and_recomputed_empty_sma():
    source = chart()
    line = populate(source)
    permutation = [3, 0, 1, 2]
    line.update_all(dates=line.source_dates[permutation], values=line.values[permutation])
    source.register_time_series("rates", line, in_gap="previous", replace=True)
    source.collapse_source_id = "rates"
    source.collapse_time_chart(debug=False)
    target = chart()
    target.restore_chart_state(source.capture_chart_state())
    assert target.collapse_source_id == "rates"
    np.testing.assert_array_equal(target.dates, source.dates)
    np.testing.assert_array_equal(target.get_time_series("rates").source_dates, line.source_dates)
    target.restore_time_chart()
    assert target.capture_chart_state()["chart"]["time"]["gaps"] is None
    empty = chart()
    empty.create_indicator(instance_id="waiting", period=4)
    target.restore_chart_state(empty.capture_chart_state())
    assert not len(target.get_time_series("indicator:waiting").values)
    target.set_data(dates=[100, 200], opens=[1, 1], highs=[2, 2], lows=[0, 0], closes=[2, 2])
    assert np.isnan(target.get_time_series("indicator:waiting").values).all()


def test_detached_registration_and_generated_bar_id():
    source = chart()
    line = PlotEconometricSeries(source.context, attach=False, dates=[100, 200], values=[1, 2])
    source.register_time_series("horizontal-bars", line)
    target = chart()
    target.restore_chart_state(source.capture_chart_state())
    target.load_horizontal_bars(num_bars=1)
    document = target.capture_chart_state()
    assert [record["id"] for record in document["series"]] == ["horizontal-bars", "horizontal-bars-2"]
    assert target.get_time_series("horizontal-bars").parent is target


def test_optional_volume_and_missing_samples_remain_mutable():
    source = chart()
    populate(source)
    snapshot = source.capture_chart_state()
    snapshot["series"][0]["data"]["volume"] = None
    target = chart()
    target.restore_chart_state(snapshot)
    assert target.capture_chart_state()["series"][0]["data"]["volume"] is None
    target.update_last_candle(close=14.5)
    target.append_candle(timestamp=START + 660, open=14, high=16, low=13, close=15, volume=30)
    assert target.volume.tolist() == [0, 0, 0, 0, 30]
    snapshot["series"][0]["data"]["volume"] = [5, 6, 8, None]
    target.restore_chart_state(snapshot)
    target.update_last_candle(close=14.5)
    assert np.isnan(target.volume[-1])


@pytest.mark.parametrize(("contents", "message"), [
    (b'{"version":1,"version":1}', "duplicate object key"),
    (b'{"chart":NaN}', "non-finite"),
    (b'{"chart":Infinity}', "non-finite"),
    (b'{"x":"\xff"}', "UTF-8"),
    (b'{"format":', "invalid UTF-8 JSON"),
])
def test_invalid_json_does_not_replace(tmp_path, contents, message):
    target = chart()
    candle = populate(target)
    path = tmp_path / "invalid.json"
    path.write_bytes(contents)
    with pytest.raises(ChartPersistenceError, match=message):
        target.open_chart(path)
    assert target.get_time_series("rates") is candle


@pytest.mark.parametrize(("change", "message"), [
    (lambda doc: doc.update(version=2), "unsupported chart version"),
    (lambda doc: doc["series"][0].update(kind="future"), r"series\[0\].kind"),
    (lambda doc: doc["series"].append(deepcopy(doc["series"][0])), "duplicate ID"),
    (lambda doc: doc["series"][1].update(id="indicator:fast"), "collides"),
    (lambda doc: doc["series"][0]["data"]["close"].pop(), r"data.close"),
    (lambda doc: doc["series"][0]["data"]["open"].__setitem__(1, None), r"open\[1\]"),
    (lambda doc: doc["series"][1]["data"]["values"].__setitem__(1, 10**400), "representable"),
    (lambda doc: doc["drawings"][0]["geometry"].update(top=5), r"geometry.top"),
    (lambda doc: doc["chart"]["time"].update(source="missing"), "unknown registration"),
    (lambda doc: doc["chart"]["time"].update(gaps=[[START, START + 120, 60]]), "adjacent source"),
])
def test_schema_validation_before_publication(change, message):
    target = chart()
    populate(target)
    target.collapse_time_chart_vec(debug=False)
    before = target.capture_chart_state()
    invalid = deepcopy(before)
    change(invalid)
    with pytest.raises(ChartPersistenceError, match=message):
        target.restore_chart_state(invalid)
    assert target.capture_chart_state() == before


def test_unowned_children_are_ignored_but_unsupported_owned_items_fail(tmp_path):
    target = chart()
    with target:
        dcg.PlotLine(target.context, X=[1], Y=[2], label="host")
    assert not target.capture_chart_state()["series"]

    class Custom(PlotEconometricSeries):
        pass

    target.register_time_series("custom", Custom(target.context, parent=target, dates=[1], values=[2]))
    path = tmp_path / "unsupported.json"
    with pytest.raises(ChartPersistenceError, match=r"custom.*unsupported"):
        target.save_chart(path)
    assert not path.exists()


def test_size_boundary_and_bounded_reads(tmp_path, monkeypatch):
    target = chart()
    path = tmp_path / "limit.json"
    with path.open("wb") as stream:
        stream.truncate(codec.MAX_DOCUMENT_BYTES + 1)
    with pytest.raises(ChartPersistenceError, match="64 MiB"):
        target.open_chart(path)

    target.save_chart(path, overwrite=True)
    data = path.read_bytes()
    monkeypatch.setattr(codec, "MAX_DOCUMENT_BYTES", len(data))
    assert codec.read_document(path) == target.capture_chart_state()
    path.write_bytes(data + b" ")
    monkeypatch.setattr(codec.os, "fstat", lambda _fd: SimpleNamespace(st_size=len(data)))
    with pytest.raises(ChartPersistenceError, match="64 MiB"):
        codec.read_document(path)
    monkeypatch.setattr(codec, "MAX_DOCUMENT_BYTES", len(data) - 1)
    with pytest.raises(ChartPersistenceError, match="64 MiB"):
        target.save_chart(path, overwrite=True)
    assert path.read_bytes() == data + b" "
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize("operation", ["fsync", "replace"])
def test_failed_file_publication_preserves_original(tmp_path, monkeypatch, operation):
    target = chart()
    path = tmp_path / "existing.json"
    path.write_bytes(b"old")
    with pytest.raises(FileExistsError):
        target.save_chart(path)

    def fail(*_args):
        raise OSError("injected failure")

    monkeypatch.setattr(codec.os, operation, fail)
    with pytest.raises(OSError, match="injected failure"):
        target.save_chart(path, overwrite=True)
    assert path.read_bytes() == b"old"
    assert list(tmp_path.iterdir()) == [path]


def test_destination_created_during_save_is_not_overwritten(tmp_path):
    path = tmp_path / "race.json"

    def publish(rename):
        path.write_bytes(b"late")
        rename()

    with pytest.raises(FileExistsError):
        codec.write_document(path, chart().capture_chart_state(), publish=publish)
    assert path.read_bytes() == b"late"
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize("fail_during", ["projection", "publication"])
def test_restore_rollback_retains_old_objects_and_view(monkeypatch, fail_during):
    target = chart()
    populate(target)
    target.X1.min, target.X1.max = START + 20, START + 210
    before = target.capture_chart_state()
    original_children = target.children
    original_tool, = target.tools
    source = chart()
    populate(source)
    source.collapse_time_chart_vec(debug=False)
    source.X1.min, source.X1.max = START + 130, START + 160
    notifications = []
    target.on_chart_restored = notifications.append

    if fail_during == "projection":
        def fail(*_args, **_kwargs):
            raise RuntimeError("projection failed")

        monkeypatch.setattr(state.GapCollapsedTimeMap, "project_many", fail)
    else:
        publish_view = state._publish_view

        def fail(*args):
            publish_view(*args)
            raise RuntimeError("publication failed")

        monkeypatch.setattr(state, "_publish_view", fail)
    with pytest.raises(RuntimeError, match=f"{fail_during} failed"):
        target.restore_chart_state(source.capture_chart_state())
    assert target.children == original_children
    assert target.tools == (original_tool,) and not original_tool.disposed
    assert target._context_menu_items["collapse"].value is False
    assert target.capture_chart_state() == before
    assert not notifications


class RenderedChart:
    def __init__(self):
        self.context = dcg.Context()
        self.viewport = self.context.viewport
        self.viewport.initialize(visible=False, width=800, height=650)
        with dcg.Window(self.context, primary=True):
            self.chart = chart(self.context, width=750, height=450, collapsed_time_cursor_tag=False)
            self.comparison = dcg.Plot(self.context, width=750, height=125)
        self.mouse = (410, 170)

    def draw(self):
        self.context.inject_mouse_pos(*self.mouse)
        self.viewport.render_frame()
        self.context.queue.submit(lambda: None).result(timeout=3)

    def until(self, condition):
        deadline = monotonic() + 5
        while not condition():
            assert monotonic() < deadline, "rendered condition did not become true"
            self.draw()

    def click(self, x, y, button=dcg.MouseButton.LEFT):
        self.mouse = (x, y)
        self.draw()
        self.draw()
        self.context.inject_mouse_down(button)
        self.draw()
        self.context.inject_mouse_up(button)
        self.draw()
        self.draw()

    def click_item(self, item):
        self.until(lambda: item.state.visible)
        x, y = item.state.pos_to_viewport
        width, height = item.state.rect_size
        self.click(x + width / 2, y + height / 2)

    def menu(self, key):
        self.click(410, 170, dcg.MouseButton.RIGHT)
        self.click_item(self.chart._context_menu_items[key])
        return self.chart._chart_file_menu


def test_rendered_menu_save_overwrite_cancel_retry_and_open(tmp_path):
    ui = RenderedChart()
    target = ui.chart
    populate(target)
    other = dcg.PlotLine(ui.context, parent=ui.comparison, X=[1, 2], Y=[3, 4], label="Other chart")
    target.X1.no_initial_fit = target.Y1.no_initial_fit = True
    target.X1.min, target.X1.max = START + 10, START + 500
    target.Y1.min, target.Y1.max = 8, 24
    for _ in range(3):
        ui.draw()
    before = target.capture_chart_state()
    path = tmp_path / "session.json"
    menu = ui.menu("save_chart")
    menu.path_input.value = str(path.with_suffix(""))
    ui.click_item(menu.action)
    ui.until(lambda: menu.window is None)
    original = path.read_bytes()

    target.update_last_candle(close=14.75)
    menu = ui.menu("save_chart")
    menu.path_input.value = str(path)
    ui.click_item(menu.action)
    ui.until(lambda: menu.action.label == "Overwrite")
    assert str(path) in menu.status.value
    ui.click_item(menu.cancel)
    assert path.read_bytes() == original
    assert menu.window is None

    menu = ui.menu("open_chart")
    menu.path_input.value = str(path)
    ui.click_item(menu.action)
    assert menu.action.label == "Replace Chart"
    ui.click_item(menu.cancel)
    assert target.closes[-1] == 14.75

    menu = ui.menu("open_chart")
    menu.path_input.value = str(tmp_path / "missing.json")
    ui.click_item(menu.action)
    ui.click_item(menu.action)
    ui.until(lambda: "Could not open" in menu.status.value)
    assert target.closes[-1] == 14.75
    target.label_overlap_debug = True
    diagnostic_item = target._diag_extents_series
    menu.path_input.value = str(path)
    ui.click_item(menu.action)
    ui.click_item(menu.action)
    ui.until(lambda: menu.window is None)
    for _ in range(3):
        ui.draw()
    assert target.closes[-1] == 14
    assert target.capture_chart_state()["chart"]["axes"] == before["chart"]["axes"]
    assert ui.comparison.children == [other]
    assert not target.label_overlap_debug and diagnostic_item.parent is None

    menu = ui.menu("save_chart")
    menu.path_input.value = str(path)
    ui.click_item(menu.action)
    ui.until(lambda: menu.action.label == "Overwrite")
    target.update_last_candle(close=14.5)
    ui.click_item(menu.action)
    ui.until(lambda: menu.window is None)
    assert path.read_bytes() != original
    assert codec.read_document(path)["series"][0]["data"]["close"][-1] == 14.5

    ui.click(410, 170, dcg.MouseButton.RIGHT)
    ui.click_item(target._context_menu_items["collapse"])
    assert target.time_is_collapsed


def test_canceled_save_cannot_publish_or_update_a_new_popup(tmp_path, monkeypatch):
    target = chart()
    menu = target._chart_file_menu
    menu.show(save=True)
    path = tmp_path / "canceled.json"
    menu.path_input.value = str(path)
    ready, release, completed = Event(), Event(), Event()
    original_write = _chart_menu.write_document

    def delayed_write(path, document, *, overwrite, publish):
        def delayed_publish(rename):
            ready.set()
            assert release.wait(5)
            publish(rename)
        try:
            original_write(path, document, overwrite=overwrite, publish=delayed_publish)
        finally:
            completed.set()

    monkeypatch.setattr(_chart_menu, "write_document", delayed_write)
    menu._submit()
    try:
        assert ready.wait(5)
        request = menu.request
        menu._submit()
        assert menu.request is request
        menu._cancel()
        menu.show(save=False)
        replacement = menu.window
    finally:
        release.set()
    assert completed.wait(5)
    target.context.queue.submit(lambda: None).result(timeout=3)
    assert not list(tmp_path.iterdir())
    assert menu.window is replacement and menu.status.value == ""
    menu._cancel()


def test_reopen_shows_a_series_hidden_from_the_native_legend(tmp_path):
    ui = RenderedChart()
    plot = ui.chart
    line = PlotEconometricSeries(
        plot.context, parent=plot, dates=[START, START + 60], values=[1, 2],
        label="A longer legend item name",
    )
    plot.register_time_series("rates", line)

    class DrawCount(dcg.CustomHandler):
        count = 0

        def check_can_bind(self, item):
            return isinstance(item, dcg.DrawInvisibleButton)

        def run(self, _item):
            self.count += 1

    def observe(item):
        counter = DrawCount(plot.context)
        button = next(child for child in item.children if isinstance(child, dcg.DrawInvisibleButton))
        button.handlers += [counter]
        return counter

    old_draw = observe(line)
    for _ in range(3):
        ui.draw()

    def click_legend(item):
        x0, y0 = plot.state.content_pos
        for y in range(int(y0) + 10, int(y0) + 35, 4):
            for x in range(int(x0) + 15, int(x0) + 90, 8):
                ui.mouse = (x, y)
                ui.draw()
                ui.draw()
                if item.legend_state.hovered:
                    ui.click(x, y)
                    return
        pytest.fail("native legend item is not clickable")

    click_legend(line)
    assert old_draw.count > 0
    hidden_at = old_draw.count
    ui.draw()
    assert old_draw.count == hidden_at
    path = tmp_path / "hidden-series.json"
    plot.save_chart(path)
    plot.open_chart(path)
    restored = plot.get_time_series("rates")
    new_draw = observe(restored)
    for _ in range(3):
        ui.draw()
    assert restored.show and restored.enabled and new_draw.count > 0
    click_legend(restored)
    hidden_at = new_draw.count
    ui.draw()
    assert new_draw.count == hidden_at
