import numpy as np
import pytest
from types import SimpleNamespace

import dearcygui as dcg

from dearcyfi import DearCyFi, PlotEconometricSeries
from dearcyfi.PyTimeLocator import locator_time3


class FakeSeries:
    def __init__(self, dates):
        self._source_dates = np.asarray(dates, dtype=float)
        self.plot_dates = self._source_dates.copy()

    @property
    def source_dates(self):
        return self._source_dates.copy()

    def set_plot_dates(self, dates):
        self.plot_dates = np.asarray(dates, dtype=float).copy()

    def restore_source_dates(self):
        self.plot_dates = self._source_dates.copy()


@pytest.fixture
def chart(monkeypatch):
    monkeypatch.setattr(DearCyFi, "_install_context_menu", lambda self: None)
    return DearCyFi(dcg.Context(), prewarm=False)


def test_registration_and_source_validation(chart):
    source = FakeSeries([0, 10, 20, 100, 110])
    chart.register_time_series("source", source)

    assert chart.time_series_ids == ("source",)
    chart.collapse_source_id = "source"
    assert chart.collapse_source_id == "source"

    with pytest.raises(ValueError, match="already registered"):
        chart.register_time_series("source", source)
    with pytest.raises(ValueError, match="Unknown collapse source"):
        chart.collapse_source_id = "missing"


def test_selected_source_drives_follower_projection_and_restoration(chart):
    source = FakeSeries([0, 10, 20, 100, 110])
    follower = FakeSeries([10, 50, 125])
    chart.register_time_series("source", source)
    chart.register_time_series("follower", follower, in_gap="previous")
    chart.collapse_source_id = "source"

    chart.collapse_time_chart(debug=False)

    np.testing.assert_array_equal(source.plot_dates, [0, 10, 20, 30, 40])
    np.testing.assert_array_equal(follower.plot_dates, [10, 20, 55])
    np.testing.assert_array_equal(follower.source_dates, [10, 50, 125])

    chart.restore_time_chart()
    np.testing.assert_array_equal(source.plot_dates, source.source_dates)
    np.testing.assert_array_equal(follower.plot_dates, follower.source_dates)


@pytest.mark.parametrize("date_context", [False, True])
def test_collapsed_axis_labels_keep_follower_dates_without_exterior_markers(
    monkeypatch, date_context
):
    base = 1_704_153_600.0  # Jan 2, midnight UTC
    chart = DearCyFi(
        dcg.Context(), prewarm=False, use_local_time=False, use_iso8601=True,
        apply_date_context_labels=date_context,
    )
    chart.set_data(
        dates=base + np.array([0, 10, 20, 86_370, 86_380]),
        opens=[1] * 5, highs=[2] * 5, lows=[0] * 5, closes=[1] * 5,
    )
    with chart:
        follower = PlotEconometricSeries(
            chart.context, dates=[base + 86_395, base - 20], values=[1, 2],
        )
    chart.register_time_series("econometric", follower)
    chart.date_context_max_gap_px = 5
    chart.date_context_min_spacing_px = 0
    offsets = [-25, -20, -10, 0, 25, 40, 50, 55, 70]
    monkeypatch.setattr(
        locator_time3.TimeAxisLocator, "__call__",
        lambda *_: [locator_time3.Tick(base + dx, 0, False, True, str(dx)) for dx in offsets],
    )
    chart.collapse_time_chart(debug=False)
    axis_info = (base - 30, base + 80, 0.1)
    chart.axes_resize_callback(None, None, [axis_info])

    np.testing.assert_array_equal(follower.plot_dates, [base + 55, base - 20])
    assert list(chart.X1.labels_coord) == [base + dx for dx in offsets]
    expected = [":35", ":40", ":50", ":00", ":20", ":40", ":50", ":55", ":10"]
    if date_context:
        expected = [
            "--01-01\n:35", "--01-01\n:40", "--01-01\n:50", "--01-02\n:00",
            "--01-02\n:20", "--01-02\n:40", "--01-02\n:50", "--01-02\n:55", "--01-03\n:10",
        ]
    assert list(chart.X1.labels) == expected

    chart.restore_time_chart()
    assert list(chart.X1.labels_coord) == [base + dx for dx in offsets]
    assert all(not label.startswith("~") for label in chart.X1.labels)


@pytest.mark.parametrize("method_name", ["collapse_time_chart", "collapse_time_chart_vec"])
def test_collapse_with_default_debug_reports_gap_and_restores(chart, capsys, method_name):
    source = FakeSeries([0, 10, 20, 100, 110])
    chart.register_time_series("source", source)
    chart.collapse_source_id = "source"

    getattr(chart, method_name)()

    np.testing.assert_array_equal(source.plot_dates, [0, 10, 20, 30, 40])
    assert "remove 70.0 seconds (delta=80.0, base=10.0)" in capsys.readouterr().out
    chart.restore_time_chart()
    np.testing.assert_array_equal(source.plot_dates, source.source_dates)


def test_removing_active_source_restores_followers_and_clears_selection(chart):
    source = FakeSeries([0, 10, 20, 100, 110])
    follower = FakeSeries([50])
    chart.register_time_series("source", source)
    chart.register_time_series("follower", follower)
    chart.collapse_source_id = "source"
    chart.collapse_time_chart(debug=False)

    chart.unregister_time_series("source")

    assert chart.collapse_source_id is None
    assert chart.time_series_ids == ("follower",)
    np.testing.assert_array_equal(follower.plot_dates, [50])


def test_set_data_registers_candles_as_backward_compatible_default(chart):
    chart.set_data(
        dates=[0, 10, 20, 100, 110],
        opens=[1, 2, 3, 4, 5],
        highs=[2, 3, 4, 5, 6],
        lows=[0, 1, 2, 3, 4],
        closes=[1.5, 2.5, 3.5, 4.5, 5.5],
    )

    assert "candles" in chart.time_series_ids
    assert chart.collapse_source_id == "candles"
    chart.collapse_time_chart_vec(debug=False)
    np.testing.assert_array_equal(chart.dates, [0, 10, 20, 30, 40])


def test_set_data_can_move_existing_candle_composite_to_another_y_axis(chart):
    candle_data = {
        "dates": [0, 10],
        "opens": [1, 2],
        "highs": [2, 3],
        "lows": [0, 1],
        "closes": [1.5, 2.5],
    }
    chart.set_data(**candle_data)
    assert chart.candlestick_plot.axes == (dcg.Axis.X1, dcg.Axis.Y1)

    chart.set_data(**candle_data, candle_y_axis=dcg.Axis.Y3)

    assert chart.candlestick_plot.y_axis == dcg.Axis.Y3
    assert chart.candlestick_plot.axes == (dcg.Axis.X1, dcg.Axis.Y3)
    assert chart.candlestick_plot._volume_bar_series.axes == (dcg.Axis.X1, dcg.Axis.Y3)


def test_context_menu_routes_to_selected_collapse_method(chart, monkeypatch):
    calls = []
    monkeypatch.setattr(
        chart,
        "collapse_time_chart",
        lambda sender=None, app_data=None, user_data=None, **kwargs: calls.append("scalar"),
    )
    monkeypatch.setattr(
        chart,
        "collapse_time_chart_vec",
        lambda sender=None, app_data=None, user_data=None, **kwargs: calls.append("vectorized"),
    )

    chart.vectorized_collapse = True
    chart._on_collapse_menu_action(SimpleNamespace(value=False), None, True)
    assert calls == ["vectorized"]

    chart.vectorized_collapse = False
    chart._on_collapse_menu_action(SimpleNamespace(value=False), None, True)
    assert calls[-1] == "scalar"

    chart._on_vectorized_menu_action(SimpleNamespace(value=True), None, False)
    assert chart.vectorized_collapse is False
    chart._on_vectorized_menu_action(SimpleNamespace(value=False), None, True)
    assert chart.vectorized_collapse is True


def test_collapse_menu_callback_uses_toggle_state_and_restores():
    chart = DearCyFi(dcg.Context(), prewarm=False)
    source = FakeSeries([0, 10, 20, 100, 110])
    chart.register_time_series("source", source)
    chart.collapse_source_id = "source"
    item = chart._context_menu_items["collapse"]

    item.callbacks[0](item, item, True)

    assert chart.time_is_collapsed
    assert item.value is True
    np.testing.assert_array_equal(source.plot_dates, [0, 10, 20, 30, 40])

    item.callbacks[0](item, item, False)

    assert not chart.time_is_collapsed
    assert item.value is False
    np.testing.assert_array_equal(source.plot_dates, source.source_dates)


def test_diagnostics_menu_callbacks_use_toggle_state():
    chart = DearCyFi(dcg.Context(), prewarm=False, apply_date_context_labels=False)
    for key, setting in (
        ("date_labels", "apply_date_context_labels"),
        ("date_debug", "date_context_debug"),
        ("overlap", "label_overlap_debug"),
        ("vectorized", "vectorized_collapse"),
    ):
        item = chart._context_menu_items[key]
        for checked in (not item.value, item.value):
            item.callbacks[0](item, item, checked)
            assert getattr(chart, setting) is checked
            assert item.value is checked


def test_context_menu_method_change_does_not_restore_collapsed_chart(chart):
    source = FakeSeries([0, 10, 20, 100, 110])
    chart.register_time_series("source", source)
    chart.collapse_source_id = "source"
    chart.collapse_time_chart_vec(debug=False)

    chart.vectorized_collapse = False

    assert chart.time_is_collapsed
    np.testing.assert_array_equal(source.plot_dates, [0, 10, 20, 30, 40])


def test_failed_collapse_restores_context_state(chart, monkeypatch):
    source = FakeSeries([0, 10, 20, 100, 110])
    chart.register_time_series("source", source)
    chart.collapse_source_id = "source"
    monkeypatch.setattr(
        chart._gap_manager,
        "collapse_dates",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("failure")),
    )

    with pytest.raises(RuntimeError, match="failure"):
        chart.collapse_time_chart(debug=False)

    assert not chart.time_is_collapsed


def test_unsupported_dearcygui_build_reports_compatibility_error(monkeypatch):
    monkeypatch.setattr(dcg, "Menu", None)
    with pytest.raises(RuntimeError, match="custom DearCyGui build"):
        DearCyFi(dcg.Context(), prewarm=False)


def test_context_menu_tooltip_attaches_explanatory_text(chart, monkeypatch):
    class FakeTooltip:
        def __init__(self, _context, **kwargs):
            self.kwargs = kwargs

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    texts = []
    monkeypatch.setattr(dcg, "Tooltip", FakeTooltip)
    monkeypatch.setattr(
        dcg,
        "Text",
        lambda _context, **kwargs: texts.append(kwargs["value"]),
    )
    target = object()
    chart._context_menu_items = {"collapse": target}
    chart._context_menu_tooltips = {}

    chart._add_context_menu_tooltip("collapse", "Restore original time.")

    assert chart._context_menu_tooltips["collapse"].kwargs["target"] is target
    assert texts == ["Restore original time."]