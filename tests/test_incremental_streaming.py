import numpy as np
import pytest

import dearcygui as dcg

from dearcyfi import DearCyFi, PlotEconometricSeries
from dearcyfi.streaming import boundary_tolerance, classify_append_spacing, infer_cadence, latest_interval_matches


@pytest.fixture
def chart():
    result = DearCyFi(dcg.Context(), prewarm=False)
    result.set_data(
        dates=[1_700_000_000.0, 1_700_000_300.0, 1_700_000_600.0],
        opens=[10.0, 11.0, 12.0],
        highs=[12.0, 13.0, 14.0],
        lows=[9.0, 10.0, 11.0],
        closes=[11.0, 12.0, 13.0],
        volume=[100.0, 200.0, 300.0],
    )
    return result


def test_latest_candle_occupancy_uses_half_open_interval_and_epoch_tolerance(chart):
    start = float(chart.candlestick_plot.source_dates[-1])

    assert chart.check_last_candle(start + 180.0) == (True, start)
    assert chart.check_last_candle(start + 300.0) == (False, start)
    assert chart.check_last_candle(start - boundary_tolerance(start, start, 300.0) / 2) == (True, start)
    tolerance = boundary_tolerance(start, start + 300.0, 300.0)
    assert chart.check_last_candle(start + 300.0 - tolerance * 2) == (True, start)
    assert chart.check_last_candle(start + 300.0 - tolerance / 2) == (False, start)
    assert chart.check_last_candle(start + 300.0 + tolerance / 2) == (False, start)


def test_five_minute_interval_matches_1000_1003_but_not_1005():
    chart = DearCyFi(dcg.Context(), prewarm=False)
    chart.set_data(
        dates=[36_000.0, 36_300.0, 36_600.0],
        opens=[10.0, 11.0, 12.0],
        highs=[12.0, 13.0, 14.0],
        lows=[9.0, 10.0, 11.0],
        closes=[11.0, 12.0, 13.0],
    )

    assert chart.check_last_candle(36_780.0) == (True, 36_600.0)
    assert chart.check_last_candle(36_900.0) == (False, 36_600.0)


def test_append_and_partial_candle_revision_keep_chart_caches_consistent(chart):
    chart.candlestick_plot.y_axis = dcg.Axis.Y3
    chart.candlestick_plot.show = False
    start = float(chart.candlestick_plot.source_dates[-1])
    chart.append_candle(
        timestamp=start + 300.0,
        open=13.0,
        high=15.0,
        low=12.0,
        close=14.0,
        volume=50.0,
    )

    np.testing.assert_array_equal(chart.candlestick_plot.source_dates[-1], start + 300.0)
    np.testing.assert_array_equal(chart.dates[-1], start + 300.0)
    np.testing.assert_array_equal(chart.opens, [10.0, 11.0, 12.0, 13.0])
    np.testing.assert_array_equal(chart.volume, [100.0, 200.0, 300.0, 50.0])
    np.testing.assert_array_equal(chart.index, [0, 1, 2, 3])
    assert chart.candlestick_plot.y_axis == dcg.Axis.Y3
    assert chart.candlestick_plot.show is False
    assert chart.candlestick_plot._volume_bar_series.axes == (dcg.Axis.X1, dcg.Axis.Y3)
    latest_button = [
        child
        for child in chart.candlestick_plot.children
        if isinstance(child, dcg.DrawInvisibleButton)
    ][-1]
    assert latest_button.user_data[0] == start + 300.0

    chart.update_last_candle(close=14.5, volume=75.0)
    assert chart.candlestick_plot.closes[-1] == 14.5
    assert chart.candlestick_plot.volumes[-1] == 75.0
    assert chart.candlestick_plot.opens[-1] == 13.0
    assert len(chart.candlestick_plot.source_dates) == 4


def test_invalid_candle_revision_and_short_append_are_transactional(chart):
    before_dates = chart.candlestick_plot.source_dates.copy()
    before_highs = np.asarray(chart.candlestick_plot.highs).copy()
    before_manager_dates = chart._gap_manager.dates_real.copy()

    with pytest.raises(ValueError, match="low <= open/close"):
        chart.update_last_candle(close=20.0)
    with pytest.raises(ValueError, match="at least one cached interval"):
        chart.append_candle(
            timestamp=float(before_dates[-1]) + 60.0,
            open=13.0,
            high=15.0,
            low=12.0,
            close=14.0,
        )
    with pytest.raises(ValueError, match="at least one field"):
        chart.update_last_candle()
    with pytest.raises(ValueError, match="finite number"):
        chart.update_last_sample("candles", close=None)

    np.testing.assert_array_equal(chart.candlestick_plot.source_dates, before_dates)
    np.testing.assert_array_equal(chart.candlestick_plot.highs, before_highs)
    np.testing.assert_array_equal(chart._gap_manager.dates_real, before_manager_dates)


@pytest.mark.parametrize("offset", [0.0, -300.0])
def test_duplicate_and_out_of_order_appends_are_rejected(chart, offset):
    latest = float(chart.candlestick_plot.source_dates[-1])

    with pytest.raises(ValueError, match="at least one cached interval"):
        chart.append_candle(
            timestamp=latest + offset,
            open=13.0,
            high=15.0,
            low=12.0,
            close=14.0,
        )


def test_collapsed_gap_extension_reprojects_only_follower_suffix(chart):
    with chart:
        follower = PlotEconometricSeries(
            chart.context,
            dates=[1_700_000_500.0, 1_700_000_750.0, 1_700_002_000.0],
            values=[1.0, 2.0, 3.0],
            tooltip=False,
        )
    chart.register_time_series("liquidity", follower, in_gap="previous")
    chart.collapse_time_chart(debug=False)
    before = follower.plot_dates

    chart.append_candle(
        timestamp=1_700_001_500.0,
        open=13.0,
        high=15.0,
        low=12.0,
        close=14.0,
    )

    after = follower.plot_dates
    assert after[0] == before[0]
    assert after[1] == pytest.approx(1_700_000_600.0)
    assert after[2] == pytest.approx(1_700_001_400.0)
    assert chart.dates[-1] == pytest.approx(1_700_000_900.0)
    assert chart._gap_manager.time_map is not None
    assert len(chart._gap_manager.time_map._segments) == 2
    chart.restore_time_chart()
    assert chart.dates[-1] == pytest.approx(1_700_001_500.0)


def test_tool_anchors_and_boundary_anchors_refresh_after_gap_append():
    chart = DearCyFi(dcg.Context(), prewarm=False, use_local_time=False)
    chart.set_data(
        dates=[0.0, 300.0, 600.0],
        opens=[10.0, 11.0, 12.0],
        highs=[12.0, 13.0, 14.0],
        lows=[9.0, 10.0, 11.0],
        closes=[11.0, 12.0, 13.0],
    )
    box = chart.add_box(left_time=750.0, bottom=10.0, right_time=88_000.0, top=12.0)
    source_geometry = box.source_geometry
    chart.collapse_time_chart(debug=False)

    chart.append_candle(
        timestamp=87_000.0,
        open=13.0,
        high=15.0,
        low=12.0,
        close=14.0,
    )

    assert box.source_geometry == source_geometry
    assert box.plot_geometry.left_time == pytest.approx(900.0)
    assert box.plot_geometry.right_time == pytest.approx(1_900.0)
    np.testing.assert_array_equal(chart._gap_manager.time_map.day_starts_real, [0.0, 87_000.0])


def test_custom_candle_index_appends_timestamp_label():
    chart = DearCyFi(dcg.Context(), prewarm=False)
    chart.set_data(
        dates=[100.0, 200.0, 300.0],
        opens=[10.0, 11.0, 12.0],
        highs=[12.0, 13.0, 14.0],
        lows=[9.0, 10.0, 11.0],
        closes=[11.0, 12.0, 13.0],
        index=["a", "b", "c"],
    )
    chart.append_candle(
        timestamp=400.0,
        open=13.0,
        high=15.0,
        low=12.0,
        close=14.0,
    )

    assert chart.index.tolist() == ["a", "b", "c", "400.0"]


def test_candle_append_extends_existing_annotations(chart):
    chart.candlestick_plot.time_counts = [[1], [], [2, 3]]
    chart.append_candle(
        timestamp=1_700_000_900.0,
        open=13.0,
        high=15.0,
        low=12.0,
        close=14.0,
    )

    assert chart.candlestick_plot.time_counts == [[1], [], [2, 3], []]


def test_scalar_series_streaming_and_projection_only_compatibility(chart):
    scalar = PlotEconometricSeries(
        chart.context,
        dates=[100.0, 160.0, 220.0],
        values=[1.0, 2.0, 3.0],
        tooltip=False,
    )
    chart.register_time_series("scalar", scalar)
    assert chart.check_last_sample("scalar", 250.0) == (True, 220.0)
    chart.append_sample("scalar", timestamp=280.0, value=4.0)
    chart.update_last_sample("scalar", value=5.0)
    np.testing.assert_array_equal(scalar.source_dates, [100.0, 160.0, 220.0, 280.0])
    np.testing.assert_array_equal(scalar.values, [1.0, 2.0, 3.0, 5.0])

    class ProjectionOnly:
        source_dates = np.array([0.0, 1.0])

        def set_plot_dates(self, dates):
            self.plot_dates = np.asarray(dates)

        def restore_source_dates(self):
            self.set_plot_dates(self.source_dates)

    projection_only = ProjectionOnly()
    chart.register_time_series("projection", projection_only)
    with pytest.raises(TypeError, match="does not support mutation"):
        chart.append_sample("projection", timestamp=2.0, value=1.0)


def test_scalar_can_drive_collapse_and_replacement_resets_candle_cadence(chart):
    with chart:
        scalar = PlotEconometricSeries(
            chart.context,
            dates=[100.0, 160.0, 220.0],
            values=[1.0, 2.0, 3.0],
            tooltip=False,
        )
    chart.register_time_series("scalar-source", scalar)
    chart.collapse_source_id = "scalar-source"
    chart.collapse_time_chart(debug=False)
    chart.append_sample("scalar-source", timestamp=400.0, value=4.0)
    assert scalar.plot_dates[-1] == pytest.approx(280.0)

    chart.set_data(
        dates=[10.0, 110.0, 210.0],
        opens=[10.0, 11.0, 12.0],
        highs=[12.0, 13.0, 14.0],
        lows=[9.0, 10.0, 11.0],
        closes=[11.0, 12.0, 13.0],
    )
    assert chart.check_last_candle(250.0) == (True, 210.0)
    assert chart._stream_cadences["candles"] == pytest.approx(100.0)


def test_spacing_helpers_validate_precision_and_cadence():
    with pytest.raises(ValueError, match="strictly increasing"):
        infer_cadence([1.0, 1.0, 2.0])
    assert infer_cadence([1.25, 2.5, 3.75]) == pytest.approx(1.25)
    assert classify_append_spacing(0.0, 300.0, 300.0) == "regular"
    assert classify_append_spacing(0.0, 750.0, 300.0) == "gap"
    assert latest_interval_matches(1_700_000_000.0, 1_700_000_180.0, 300.0)
    with pytest.raises(ValueError, match="precision"):
        boundary_tolerance(1e16, 1e16, 1.0)


def test_empty_singleton_unknown_and_invalid_timestamp_errors(chart):
    with pytest.raises(ValueError, match="Unknown time series"):
        chart.check_last_sample("missing", 0.0)
    with pytest.raises(ValueError, match="finite Unix timestamp"):
        chart.check_last_candle(np.nan)

    with chart:
        empty = PlotEconometricSeries(
            chart.context,
            dates=[],
            values=[],
            tooltip=False,
        )
        singleton = PlotEconometricSeries(
            chart.context,
            dates=[10.0],
            values=[1.0],
            tooltip=False,
        )
    chart.register_time_series("empty", empty)
    chart.register_time_series("singleton", singleton)
    assert chart.check_last_sample("empty", 0.0) == (False, None)
    with pytest.raises(ValueError, match="at least two finite"):
        chart.append_sample("empty", timestamp=1.0, value=2.0)
    with pytest.raises(ValueError, match="at least two finite"):
        chart.check_last_sample("singleton", 10.0)


@pytest.mark.parametrize("collapsed", [False, True])
@pytest.mark.parametrize("gap_days", [2.0, 2.5])
def test_daily_cadence_rejects_short_spacing_and_accepts_longer_gap(collapsed, gap_days):
    chart = DearCyFi(dcg.Context(), prewarm=False)
    chart.set_data(
        dates=[0.0, 86_400.0, 172_800.0],
        opens=[10.0, 11.0, 12.0],
        highs=[12.0, 13.0, 14.0],
        lows=[9.0, 10.0, 11.0],
        closes=[11.0, 12.0, 13.0],
    )
    if collapsed:
        chart.collapse_time_chart(debug=False)
    with pytest.raises(ValueError, match="at least one cached interval"):
        chart.append_candle(
            timestamp=172_800.0 + 14_400.0,
            open=13.0,
            high=15.0,
            low=12.0,
            close=14.0,
        )

    chart.append_candle(
        timestamp=172_800.0 + gap_days * 86_400.0,
        open=13.0,
        high=15.0,
        low=12.0,
        close=14.0,
    )
    expected = 172_800.0 + (86_400.0 if collapsed else gap_days * 86_400.0)
    assert chart.dates[-1] == pytest.approx(expected)
    if not collapsed:
        chart.collapse_time_chart(debug=False)
        assert chart.dates[-1] == pytest.approx(172_800.0 + 86_400.0)


@pytest.mark.parametrize(
    ("policy", "expected_inside_gap"),
    [("next", 1_700_000_900.0), ("previous", 1_700_000_600.0)],
)
def test_gap_tail_reprojection_honors_each_follower_policy(chart, policy, expected_inside_gap):
    with chart:
        follower = PlotEconometricSeries(
            chart.context,
            dates=[1_700_000_750.0, 1_700_001_500.0, 1_700_002_000.0],
            values=[2.0, 2.5, 3.0],
            tooltip=False,
        )
    chart.register_time_series("follower", follower, in_gap=policy)
    chart.collapse_time_chart(debug=False)
    chart.append_candle(
        timestamp=1_700_001_500.0,
        open=13.0,
        high=15.0,
        low=12.0,
        close=14.0,
    )
    assert follower.plot_dates[0] == pytest.approx(expected_inside_gap)
    assert follower.plot_dates[1] == pytest.approx(1_700_000_900.0)
    assert follower.plot_dates[2] == pytest.approx(1_700_001_400.0)


def test_uncollapsed_gap_append_does_not_change_follower_projection(chart):
    with chart:
        follower = PlotEconometricSeries(
            chart.context,
            dates=[1_700_000_750.0, 1_700_002_000.0],
            values=[2.0, 3.0],
            tooltip=False,
        )
    chart.register_time_series("follower", follower)
    box = chart.add_box(
        left_time=1_700_000_750.0,
        bottom=10.0,
        right_time=1_700_002_000.0,
        top=12.0,
    )
    before = follower.plot_dates
    before_box = box.plot_geometry

    chart.append_candle(
        timestamp=1_700_001_500.0,
        open=13.0,
        high=15.0,
        low=12.0,
        close=14.0,
    )

    np.testing.assert_array_equal(follower.plot_dates, before)
    assert box.plot_geometry == before_box


def test_stream_failure_restores_source_map_follower_and_cached_dates(chart):
    class FailOnceFollower:
        def __init__(self):
            self._source_dates = np.array([1_700_000_750.0, 1_700_002_000.0])
            self.plot_dates = self._source_dates.copy()
            self.fail_next = False

        @property
        def source_dates(self):
            return self._source_dates.copy()

        def set_plot_dates(self, dates):
            if self.fail_next:
                self.fail_next = False
                raise RuntimeError("injected follower publication failure")
            self.plot_dates = np.asarray(dates, dtype=float).copy()

        def restore_source_dates(self):
            self.set_plot_dates(self._source_dates)

    follower = FailOnceFollower()
    chart.register_time_series("follower", follower)
    chart.collapse_time_chart(debug=False)
    previous_map = chart._gap_manager.time_map
    previous_source = chart.candlestick_plot.source_dates
    previous_follower = follower.plot_dates.copy()
    previous_chart_dates = chart.dates.copy()
    follower.fail_next = True

    with pytest.raises(RuntimeError, match="injected follower"):
        chart.append_candle(
            timestamp=1_700_001_500.0,
            open=13.0,
            high=15.0,
            low=12.0,
            close=14.0,
        )

    np.testing.assert_array_equal(chart.candlestick_plot.source_dates, previous_source)
    np.testing.assert_array_equal(follower.plot_dates, previous_follower)
    np.testing.assert_array_equal(chart.dates, previous_chart_dates)
    assert chart._gap_manager.time_map is previous_map
    assert chart._gap_manager.time_is_collapsed


def test_steady_source_append_avoids_full_gap_builders(chart, monkeypatch):
    chart.collapse_time_chart(debug=False)
    import dearcyfi.core as core_module

    original_infer = core_module.infer_cadence
    inference_calls = []

    def tracked_infer(timestamps):
        inference_calls.append(1)
        return original_infer(timestamps)

    monkeypatch.setattr(core_module, "infer_cadence", tracked_infer)

    def unexpected_scan(*_args, **_kwargs):
        raise AssertionError("steady append invoked a full-history gap builder")

    monkeypatch.setattr(chart._gap_manager, "find_gaps_and_chunks", unexpected_scan)
    chart.append_candle(
        timestamp=1_700_000_900.0,
        open=13.0,
        high=15.0,
        low=12.0,
        close=14.0,
    )
    chart.append_candle(
        timestamp=1_700_001_200.0,
        open=14.0,
        high=16.0,
        low=13.0,
        close=15.0,
    )
    assert len(inference_calls) == 1


def test_streaming_candle_render_reuses_loaded_tooltip_and_volume_cadence(chart, monkeypatch):
    import dearcyfi.DCG_Candle_Utils as candle_module

    def unexpected_median(*_args, **_kwargs):
        raise AssertionError("streaming candle render recomputed a timestamp median")

    monkeypatch.setattr(candle_module, "_median_candle_delta_seconds", unexpected_median)
    chart.append_candle(
        timestamp=1_700_000_900.0,
        open=13.0,
        high=15.0,
        low=12.0,
        close=14.0,
    )


def test_candle_follower_gap_reprojection_reuses_loaded_cadence(chart, monkeypatch):
    with chart:
        scalar = PlotEconometricSeries(
            chart.context,
            dates=[100.0, 160.0, 220.0],
            values=[1.0, 2.0, 3.0],
            tooltip=False,
        )
    chart.register_time_series("scalar-source", scalar)
    chart.collapse_source_id = "scalar-source"
    chart.collapse_time_chart(debug=False)

    import dearcyfi.DCG_Candle_Utils as candle_module

    def unexpected_median(*_args, **_kwargs):
        raise AssertionError("candle follower projection recomputed a timestamp median")

    monkeypatch.setattr(candle_module, "_median_candle_delta_seconds", unexpected_median)
    chart.append_sample("scalar-source", timestamp=400.0, value=4.0)
