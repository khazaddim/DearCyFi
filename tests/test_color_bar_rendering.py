import numpy as np
import pytest

import dearcygui as dcg

from dearcyfi.DCG_Candle_Utils import PlotCandleStick
from dearcyfi.core import DearCyFi


@pytest.fixture
def context():
    return dcg.Context()


def _candle(context, *, volumes=None, volume_kwargs=None):
    if volumes is None:
        volumes = np.array([10.0, 20.0, 0.0])
    return PlotCandleStick(
        context,
        dates=np.array([10.0, 20.0, 30.0]),
        opens=np.array([2.0, 4.0, 3.0]),
        closes=np.array([3.0, 2.0, 3.0]),
        lows=np.array([1.0, 1.0, 2.0]),
        highs=np.array([4.0, 5.0, 4.0]),
        volumes=volumes,
        volume_kwargs=volume_kwargs,
    )


def test_candle_volume_uses_normalized_bottom_anchored_color_bars(context):
    candle = _candle(context)
    bars = candle._volume_bar_series

    assert isinstance(bars, dcg.PlotColorBars)
    assert bars.anchor == "axis_min"
    assert bars.value_space == "normalized"
    assert bars.normalized_max_fraction == pytest.approx(0.20)
    assert bars.ignore_fit is True
    assert list(bars.Y) == pytest.approx([0.5, 1.0, 0.0])
    assert [dcg.color_as_int(color) for color in bars.colors] == [
        candle._bull_color,
        candle._bear_color,
        candle._bull_color,
    ]


@pytest.mark.parametrize(
    ("volumes", "expected"),
    [
        (np.array([]), []),
        (np.array([0.0, 0.0, 0.0]), [0.0, 0.0, 0.0]),
        (np.array([-2.0, 4.0, np.nan]), [0.0, 1.0, 0.0]),
    ],
)
def test_candle_volume_normalization_handles_non_positive_inputs(
    context, volumes, expected
):
    candle = _candle(context, volumes=volumes)

    assert list(candle._volume_bar_series.Y) == pytest.approx(expected)
    np.testing.assert_equal(candle.volumes, volumes)


def test_candle_volume_accepts_broadcast_color_override(context):
    override = (12, 34, 56, 200)
    candle = _candle(context, volume_kwargs={"colors": override})

    assert len(candle._volume_bar_series.colors) == 1
    assert dcg.color_as_int(candle._volume_bar_series.colors[0]) == dcg.color_as_int(override)


def test_candle_volume_preserves_weight_override(context):
    candle = _candle(context, volume_kwargs={"weight": 3.5})

    candle.update_all(
        dates=np.array([10.0, 20.0]),
        opens=np.array([2.0, 3.0]),
        closes=np.array([2.5, 2.0]),
        lows=np.array([1.0, 1.5]),
        highs=np.array([3.0, 3.5]),
        volumes=np.array([4.0, 8.0]),
    )

    assert candle._volume_bar_series.weight == pytest.approx(3.5)


def test_candle_volume_rejects_mismatched_per_bar_colors(context):
    with pytest.raises(ValueError, match="colors must be empty, a single color, or one color per bar"):
        _candle(
            context,
            volume_kwargs={"colors": [(255, 0, 0, 255), (0, 255, 0, 255)]},
        )


def test_candle_volume_count_change_is_validation_safe(context):
    candle = _candle(context)

    candle.update_all(
        dates=np.array([10.0, 20.0]),
        opens=np.array([2.0, 3.0]),
        closes=np.array([2.5, 2.0]),
        lows=np.array([1.0, 1.5]),
        highs=np.array([3.0, 3.5]),
        volumes=np.array([0.0, 8.0]),
    )

    assert list(candle._volume_bar_series.X) == pytest.approx([10.0, 20.0])
    assert list(candle._volume_bar_series.Y) == pytest.approx([0.0, 1.0])
    assert len(candle._volume_bar_series.colors) == 2


def test_horizontal_bars_use_native_anchor_and_survive_count_change(context):
    chart = DearCyFi(context, prewarm=False)

    chart.load_horizontal_bars(num_bars=3)
    bars = chart.horizontal_bars
    chart.load_horizontal_bars(num_bars=5, value_space="normalized")

    assert isinstance(bars, dcg.PlotColorBars)
    assert bars.horizontal is True
    assert bars.anchor == "axis_max"
    assert bars.ignore_fit is True
    assert bars.axes == (dcg.Axis.X1, dcg.Axis.Y1)
    assert bars.value_space == "normalized"
    assert len(bars.X) == len(bars.Y) == 5
    assert min(bars.X) >= 0.0
    assert max(bars.X) == pytest.approx(1.0)