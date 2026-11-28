import numpy as np
import pytest

import dearcygui as dcg

from dearcyfi import (
    DearCyFi,
    CandleSnapshot,
    PlotCandleIndicatorSeries,
    SMA,
)


def candle_snapshot(close=(1.0, 2.0, 3.0, 4.0)):
    close = np.asarray(close, dtype=float)
    count = close.size
    return CandleSnapshot(
        dates=np.arange(count, dtype=float) * 300.0,
        opens=close - 0.1,
        highs=close + 1.0,
        lows=close - 1.0,
        closes=close,
    )


def test_sma_known_values_and_period_one():
    close = candle_snapshot([1.0, 2.0, 3.0, 4.0])
    np.testing.assert_allclose(SMA(period=3, field="close").calculate(close)["sma"], [np.nan, np.nan, 2.0, 3.0])
    np.testing.assert_allclose(SMA(period=1).calculate(close)["sma"], [1.0, 2.0, 3.0, 4.0])


@pytest.mark.parametrize("field", ["open", "high", "low", "close"])
def test_sma_selects_each_ohlc_field(field):
    snapshot = candle_snapshot([1.0, 2.0, 3.0, 4.0])
    result = SMA(period=1, field=field).calculate(snapshot)["sma"]
    np.testing.assert_allclose(result, snapshot.field(field))


def test_sma_preserves_observation_gaps_and_breaks_nonfinite_windows():
    snapshot = CandleSnapshot(
        dates=np.array([0.0, 300.0, 1000.0, 1300.0]),
        opens=np.array([1.0, 2.0, 3.0, 4.0]),
        highs=np.array([2.0, 3.0, 4.0, 5.0]),
        lows=np.array([0.0, 1.0, 2.0, 3.0]),
        closes=np.array([1.0, np.nan, 3.0, 4.0]),
    )
    np.testing.assert_allclose(
        SMA(period=2).calculate(snapshot)["sma"],
        [np.nan, np.nan, np.nan, 3.5],
        equal_nan=True,
    )


@pytest.mark.parametrize("period", [True, 0, -1, 1.5, np.nan])
def test_sma_rejects_invalid_period(period):
    with pytest.raises(ValueError, match="positive integer"):
        SMA(period=period)


@pytest.mark.parametrize("field", ["", "volume", "adjclose", None])
def test_sma_rejects_invalid_field(field):
    with pytest.raises(ValueError, match="open, high, low, close"):
        SMA(field=field)


@pytest.fixture
def chart():
    result = DearCyFi(dcg.Context(), prewarm=False)
    result.set_data(
        dates=[0.0, 300.0, 600.0, 900.0],
        opens=[1.0, 2.0, 3.0, 4.0],
        highs=[2.0, 3.0, 4.0, 5.0],
        lows=[0.0, 1.0, 2.0, 3.0],
        closes=[1.0, 2.0, 3.0, 4.0],
    )
    return result


def test_chart_manager_create_edit_remove_duplicate_instances(chart):
    first = chart.create_indicator(type="SMA", period=2, field="close")
    second = chart.create_indicator(type="SMA", period=2, field="close")

    assert first.instance_id != second.instance_id
    assert chart.indicator_ids == (first.instance_id, second.instance_id)
    assert isinstance(first.series, dcg.DrawInPlot)
    assert first.series.no_legend is False
    np.testing.assert_allclose(first.series.values, [np.nan, 1.5, 2.5, 3.5])

    first.series.show = False
    updated = chart.edit_indicator(first.instance_id, period=3, field="high")
    assert updated.instance_id == first.instance_id
    assert updated.series is first.series
    assert updated.series.show is False
    np.testing.assert_allclose(updated.series.values, [np.nan, np.nan, 3.0, 4.0])

    chart.remove_indicator(first.instance_id)
    assert chart.indicator_ids == (second.instance_id,)
    assert first.registration_id not in chart.time_series_ids
    assert second.registration_id in chart.time_series_ids


def test_indicator_line_colors_are_independent_validated_and_preserved(chart):
    first_color = (20, 40, 60, 255)
    second_color = (200, 150, 100, 255)
    first = chart.create_indicator(period=2, field="close", line_color=first_color)
    second = chart.create_indicator(period=2, field="close", line_color=second_color)

    assert first.series.line_color == first_color
    assert second.series.line_color == second_color
    first_line = next(child for child in first.series.children if isinstance(child, dcg.DrawPolyline))
    assert first_line.color == pytest.approx([20 / 255, 40 / 255, 60 / 255, 1.0])

    first.series.show = False
    before_children = list(first.series.children)
    with pytest.raises(ValueError, match="line_color"):
        chart.edit_indicator(first.instance_id, line_color=(1, 2, 3))
    assert first.series.line_color == first_color
    assert first.series.children == before_children

    edited_color = (80, 100, 120, 255)
    chart.edit_indicator(first.instance_id, line_color=edited_color)
    assert first.series.line_color == edited_color
    assert second.series.line_color == second_color
    assert first.series.show is False
    assert [child.color for child in first.series.children if isinstance(child, dcg.DrawPolyline)] == [
        pytest.approx([80 / 255, 100 / 255, 120 / 255, 1.0])
    ]

    chart.update_last_candle(close=4.5)
    assert first.series.line_color == edited_color
    updated_line = next(
        child for child in first.series.children if isinstance(child, dcg.DrawPolyline)
    )
    assert updated_line.color == pytest.approx([80 / 255, 100 / 255, 120 / 255, 1.0])
    chart.edit_indicator(first.instance_id, period=3)
    assert first.series.line_color == edited_color


def test_indicator_line_color_is_applied_to_every_finite_run():
    context = dcg.Context()
    series = PlotCandleIndicatorSeries(
        context,
        indicator_id="gapped-color-test",
        calculator=SMA(period=1),
        candles=candle_snapshot([1.0, 2.0, np.nan, 4.0, 5.0]),
        line_color=(10, 20, 30, 255),
    )
    polylines = [child for child in series.children if isinstance(child, dcg.DrawPolyline)]

    assert len(polylines) == 2
    assert all(
        line.color == pytest.approx([10 / 255, 20 / 255, 30 / 255, 1.0])
        for line in polylines
    )


@pytest.mark.parametrize(
    "line_color",
    [(1, 2, 3), (1, 2, 3, 256), (1, 2.0, 3, 4), (1, 2, 3, True), np.array(1)],
)
def test_indicator_rejects_invalid_line_colors_on_creation(chart, line_color):
    with pytest.raises(ValueError, match="line_color"):
        chart.create_indicator(period=2, field="close", line_color=line_color)
    assert chart.indicator_ids == ()


def test_invalid_edit_does_not_mutate(chart):
    instance = chart.create_indicator(period=2, field="close")
    before_values = instance.series.values.copy()
    before_label = instance.series.label

    with pytest.raises(ValueError, match="positive integer"):
        chart.edit_indicator(instance.instance_id, period=0, field="close")

    np.testing.assert_array_equal(instance.series.values, before_values)
    assert instance.series.label == before_label
    assert chart.indicator_manager.get(instance.instance_id).calculator.period == 2


def test_stream_revision_append_and_full_replacement_recompute(chart):
    instance = chart.create_indicator(period=2, field="close")

    chart.update_last_candle(close=4.5)
    np.testing.assert_allclose(instance.series.values, [np.nan, 1.5, 2.5, 3.75])

    chart.update_last_candle(close=4.8)
    np.testing.assert_allclose(instance.series.values, [np.nan, 1.5, 2.5, 3.9])

    chart.append_candle(timestamp=1200.0, open=5.0, high=6.0, low=4.5, close=5.5)
    np.testing.assert_allclose(instance.series.values, [np.nan, 1.5, 2.5, 3.9, 5.15])
    assert len(instance.series.source_dates) == 5

    chart.set_data(
        dates=[10.0, 310.0],
        opens=[5.0, 6.0],
        highs=[7.0, 8.0],
        lows=[4.0, 5.0],
        closes=[6.0, 7.0],
    )
    np.testing.assert_allclose(instance.series.values, [np.nan, 6.5])
    np.testing.assert_array_equal(instance.series.source_dates, [10.0, 310.0])


def test_collapsed_create_and_alternative_collapse_source(chart):
    chart.collapse_time_chart(debug=False)
    instance = chart.create_indicator(period=2, field="close")

    np.testing.assert_array_equal(instance.series.source_dates, chart.candlestick_plot.source_dates)
    assert len(instance.series.plot_dates) == 4
    assert instance.series.plot_dates is not instance.series.source_dates

    chart.restore_time_chart()
    np.testing.assert_array_equal(instance.series.plot_dates, instance.series.source_dates)


def test_series_preserves_line_breaks_and_source_tooltip_data():
    context = dcg.Context()
    snapshot = CandleSnapshot(
        dates=[10.0, 20.0, 30.0],
        opens=[1.0, 2.0, 3.0],
        highs=[2.0, 3.0, 4.0],
        lows=[0.0, 1.0, 2.0],
        closes=[1.0, np.nan, 3.0],
    )
    series = PlotCandleIndicatorSeries(
        context,
        indicator_id="test-indicator",
        calculator=SMA(period=2),
        candles=snapshot,
    )
    polylines = [child for child in series.children if isinstance(child, dcg.DrawPolyline)]
    buttons = [child for child in series.children if isinstance(child, dcg.DrawInvisibleButton)]
    assert polylines == []
    assert not np.isfinite(series.values).all()
    assert all(button.parent is series for button in buttons)


def test_indicator_rejects_direct_chart_and_series_mutation(chart):
    instance = chart.create_indicator(period=2, field="close")

    with pytest.raises(TypeError, match="derived"):
        chart.append_sample(instance.registration_id, timestamp=1200.0, value=99.0)
    with pytest.raises(TypeError, match="derived"):
        instance.series.update_all(dates=[1.0], values=[2.0])


def test_indicator_calculation_failure_does_not_mutate_candle(chart):
    instance = chart.create_indicator(period=2, field="close")
    before_dates = chart.dates.copy()
    manager = chart.indicator_manager
    original = manager.prepare_candle_state

    def fail_prepare(prepared):
        raise RuntimeError("injected indicator calculation failure")

    manager.prepare_candle_state = fail_prepare
    try:
        with pytest.raises(RuntimeError, match="calculation"):
            chart.append_candle(
                timestamp=1200.0,
                open=5.0,
                high=6.0,
                low=4.5,
                close=5.5,
            )
    finally:
        manager.prepare_candle_state = original

    np.testing.assert_array_equal(chart.dates, before_dates)
    np.testing.assert_array_equal(instance.series.source_dates, [0.0, 300.0, 600.0, 900.0])


def test_indicator_publication_failure_rolls_back_append_once(chart):
    instance = chart.create_indicator(period=2, field="close")
    before_dates = chart.dates.copy()
    before_values = instance.series.values.copy()
    original = instance.series.apply_calculation_update
    failed = {"value": False}

    def fail_once(**kwargs):
        if not failed["value"]:
            failed["value"] = True
            raise RuntimeError("injected indicator publication failure")
        return original(**kwargs)

    instance.series.apply_calculation_update = fail_once
    try:
        with pytest.raises(RuntimeError, match="publication"):
            chart.append_candle(
                timestamp=1200.0,
                open=5.0,
                high=6.0,
                low=4.5,
                close=5.5,
            )
    finally:
        instance.series.apply_calculation_update = original

    np.testing.assert_array_equal(chart.dates, before_dates)
    np.testing.assert_array_equal(instance.series.source_dates, [0.0, 300.0, 600.0, 900.0])
    np.testing.assert_array_equal(instance.series.values, before_values)
