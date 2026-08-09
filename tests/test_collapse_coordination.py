import numpy as np
import pytest

import dearcygui as dcg

from dearcyfi import DearCyFi


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
def chart():
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
    assert chart.candlestick_plot._volume_digital_series.axes == (dcg.Axis.X1, dcg.Axis.Y3)