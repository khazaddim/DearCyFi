import numpy as np
import pytest

import dearcygui as dcg

from dearcyfi import DearCyFi
from dearcyfi.DCG_Candle_Utils import PlotCandleStick
from dearcyfi.PyTimeLocator import locator_time3


@pytest.fixture
def context():
    return dcg.Context()


@pytest.fixture
def chart(context):
    return DearCyFi(context, prewarm=False, use_local_time=False)


@pytest.fixture
def candle_plot(context):
    return PlotCandleStick(
        context,
        dates=np.array([0.0, 10.0, 20.0], dtype=float),
        source_dates=np.array([100.0, 110.0, 120.0], dtype=float),
        opens=np.array([10.0, 8.0, 7.0], dtype=float),
        closes=np.array([11.0, 6.0, 7.0], dtype=float),
        lows=np.array([9.0, 5.0, 6.0], dtype=float),
        highs=np.array([12.0, 9.0, 8.0], dtype=float),
        volumes=np.array([1.0, 1.0, 1.0], dtype=float),
        weight=0.25,
        tooltip=False,
    )


def _load_chart_candles(chart: DearCyFi) -> None:
    chart.set_data(
        dates=[0.0, 10.0, 20.0, 100.0, 110.0],
        opens=[10.0, 8.0, 7.0, 5.0, 9.0],
        highs=[12.0, 9.0, 8.0, 7.0, 10.0],
        lows=[9.0, 5.0, 6.0, 4.0, 8.0],
        closes=[11.0, 6.0, 7.0, 6.0, 8.0],
        volume=[1.0, 1.0, 1.0, 1.0, 1.0],
    )


@pytest.mark.parametrize(
    "spec",
    [
        locator_time3.DateTimeSpec(locator_time3.DATE_DAY_MO_YR, locator_time3.TIMEFMT_HR_MIN),
        locator_time3.DateTimeSpec(locator_time3.DATE_NONE, locator_time3.TIMEFMT_HR_MIN_S, use_24_hour=True),
        locator_time3.DateTimeSpec(locator_time3.DATE_YR, locator_time3.TIMEFMT_NONE, use_iso8601=True),
    ],
)
def test_formats_supported_datetime_specs(chart, spec):
    chart.cursor_tag_formatter = spec
    expected = locator_time3.format_datetime(
        locator_time3.ImPlotTime.from_double(61.0),
        spec,
        use_local_time=False,
        use_24_hour=bool(chart._time_locator_use_24_hour or spec.use_24_hour),
        use_iso8601=bool(chart._time_locator_use_iso8601 or spec.use_iso8601),
    )

    assert chart.format_cursor_tag_text_for_plot_x(61.0) == expected


def test_custom_formatter_receives_expanded_real_timestamp(chart):
    _load_chart_candles(chart)
    chart.collapse_time_chart(debug=False)
    calls = []
    chart.cursor_tag_formatter = lambda timestamp: calls.append(timestamp) or f"ts={timestamp:.1f}"

    text = chart.format_cursor_tag_text_for_plot_x(25.0)

    assert text == f"ts={chart._gap_manager.time_map.expand(25.0):.1f}"
    assert calls == [chart._gap_manager.time_map.expand(25.0)]


def test_collapsed_and_restored_cursor_time_conversion(chart):
    _load_chart_candles(chart)

    assert chart.expand_cursor_plot_x_to_real_time(100.0) == 100.0

    chart.collapse_time_chart(debug=False)
    collapsed_x = 30.0
    expected_real = chart._gap_manager.time_map.expand(collapsed_x)
    assert chart.expand_cursor_plot_x_to_real_time(collapsed_x) == expected_real

    chart.restore_time_chart()
    assert chart.expand_cursor_plot_x_to_real_time(100.0) == 100.0


def test_cursor_bridge_coordinates_use_time_map_expand_behavior(chart):
    _load_chart_candles(chart)
    chart.collapse_time_chart(debug=False)

    bridge_x = 25.0
    assert chart.expand_cursor_plot_x_to_real_time(bridge_x) == chart._gap_manager.time_map.expand(bridge_x)


def test_invalid_cursor_configuration_and_output_raise_clear_errors(context):
    with pytest.raises(TypeError, match="DateTimeSpec, callable, or None"):
        DearCyFi(context, prewarm=False, cursor_tag_formatter=123)

    chart = DearCyFi(context, prewarm=False, cursor_tag_formatter=lambda _timestamp: 123)
    with pytest.raises(TypeError, match="must return a string"):
        chart.format_cursor_tag_text_for_plot_x(10.0)


def test_invalid_cursor_coordinates_hide_tag(chart):
    chart._update_cursor_tag_from_plot_x(10.0)
    assert chart.cursor_tag.show is True

    chart._update_cursor_tag_from_plot_x(np.nan)

    assert chart.cursor_tag.show is False


def test_cursor_plot_bounds_exclude_axis_strip(chart):
    chart.X1.min = 0.0
    chart.X1.max = 100.0
    chart.Y1.min = 10.0
    chart.Y1.max = 20.0

    assert chart._cursor_is_inside_plot(50.0, 15.0) is True
    assert chart._cursor_is_inside_plot(50.0, 9.0) is False
    assert chart._cursor_is_inside_plot(101.0, 15.0) is False


def test_cursor_tag_state_uses_semantic_colors(chart):
    _load_chart_candles(chart)

    bullish = chart.get_cursor_tag_state_for_plot_x(0.0)
    bearish = chart.get_cursor_tag_state_for_plot_x(10.0)
    neutral = chart.get_cursor_tag_state_for_plot_x(50.0)

    assert bullish["bg_color"] == chart.cursor_tag_bullish_color
    assert bearish["bg_color"] == chart.cursor_tag_bearish_color
    assert neutral["bg_color"] == chart.cursor_tag_no_candle_color


def test_cursor_tag_can_be_disabled_without_forcing_mouse_pos(context):
    chart = DearCyFi(context, prewarm=False, collapsed_time_cursor_tag=False, no_mouse_pos=False)

    assert chart.cursor_tag is None
    assert chart.no_mouse_pos is False

    chart.cursor_tag_enabled = True
    assert chart.no_mouse_pos is True

    chart.cursor_tag_enabled = False
    assert chart.no_mouse_pos is False


def test_candle_lookup_identifies_bullish_bearish_and_equal_close(candle_plot):
    assert candle_plot.get_candle_direction_for_x(0.0) == "bullish"
    assert candle_plot.get_candle_direction_for_x(10.0) == "bearish"
    assert candle_plot.get_candle_direction_for_x(20.0) == "bullish"


def test_candle_lookup_uses_half_median_spacing_bands(context):
    candle_plot = PlotCandleStick(
        context,
        dates=np.array([0.0, 10.0], dtype=float),
        source_dates=np.array([100.0, 110.0], dtype=float),
        opens=np.array([1.0, 2.0], dtype=float),
        closes=np.array([2.0, 1.0], dtype=float),
        lows=np.array([0.0, 0.0], dtype=float),
        highs=np.array([3.0, 3.0], dtype=float),
        volumes=np.array([1.0, 1.0], dtype=float),
        weight=0.1,
        tooltip=False,
    )
    empty_plot = PlotCandleStick(
        context,
        dates=np.array([], dtype=float),
        source_dates=np.array([], dtype=float),
        opens=np.array([], dtype=float),
        closes=np.array([], dtype=float),
        lows=np.array([], dtype=float),
        highs=np.array([], dtype=float),
        volumes=np.array([], dtype=float),
        tooltip=False,
    )

    assert candle_plot.get_candle_direction_for_x(5.0) == "bullish"
    assert candle_plot.get_candle_direction_for_x(15.0) == "bearish"
    assert candle_plot.get_candle_direction_for_x(-5.01) is None
    assert candle_plot.get_candle_direction_for_x(15.01) is None
    assert empty_plot.get_candle_direction_for_x(0.0) is None


def test_candle_lookup_uses_rendered_collapsed_coordinates(context):
    candle_plot = PlotCandleStick(
        context,
        dates=np.array([0.0, 10.0, 20.0], dtype=float),
        source_dates=np.array([100.0, 200.0, 300.0], dtype=float),
        opens=np.array([1.0, 3.0, 2.0], dtype=float),
        closes=np.array([2.0, 2.0, 4.0], dtype=float),
        lows=np.array([0.0, 1.0, 1.0], dtype=float),
        highs=np.array([3.0, 4.0, 5.0], dtype=float),
        volumes=np.array([1.0, 1.0, 1.0], dtype=float),
        tooltip=False,
    )
    candle_plot.update(dates=np.array([0.0, 5.0, 10.0], dtype=float))

    assert candle_plot.get_candle_direction_for_x(5.0) == "bearish"
    assert candle_plot.get_candle_direction_for_x(2.5) == "bullish"
    assert candle_plot.get_candle_direction_for_x(12.51) is None


def test_candle_lookup_resolves_overlaps_by_nearest_center(context):
    candle_plot = PlotCandleStick(
        context,
        dates=np.array([0.0, 1.0, 2.0], dtype=float),
        source_dates=np.array([10.0, 20.0, 30.0], dtype=float),
        opens=np.array([5.0, 3.0, 4.0], dtype=float),
        closes=np.array([4.0, 6.0, 2.0], dtype=float),
        lows=np.array([3.0, 2.0, 1.0], dtype=float),
        highs=np.array([6.0, 7.0, 5.0], dtype=float),
        volumes=np.array([1.0, 1.0, 1.0], dtype=float),
        weight=1.1,
        tooltip=False,
    )

    assert candle_plot.get_candle_direction_for_x(1.4) == "bullish"