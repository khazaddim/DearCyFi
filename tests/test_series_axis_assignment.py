import numpy as np
import pytest

import dearcygui as dcg

from dearcyfi.DCG_Candle_Utils import PlotCandleStick


@pytest.fixture
def context():
    return dcg.Context()


def _candle(context, **kwargs):
    return PlotCandleStick(
        context,
        dates=np.array([10.0, 20.0]),
        opens=np.array([2.0, 3.0]),
        highs=np.array([3.0, 4.0]),
        lows=np.array([1.0, 2.0]),
        closes=np.array([2.5, 3.5]),
        volumes=np.array([0.1, 0.2]),
        **kwargs,
    )


@pytest.mark.parametrize("y_axis", [dcg.Axis.Y1, dcg.Axis.Y2, dcg.Axis.Y3])
def test_y_axis_propagates_to_complete_candle_composite(context, y_axis):
    candle = _candle(context, y_axis=y_axis)

    expected_axes = (dcg.Axis.X1, y_axis)
    assert candle.y_axis == y_axis
    assert candle.axes == expected_axes
    assert candle._volume_bar_series.axes == expected_axes


def test_candle_y_axis_defaults_to_y1(context):
    candle = _candle(context)

    assert candle.y_axis == dcg.Axis.Y1
    assert candle.axes == (dcg.Axis.X1, dcg.Axis.Y1)
    assert candle._volume_bar_series.axes == (dcg.Axis.X1, dcg.Axis.Y1)


def test_candle_y_axis_update_moves_complete_composite(context):
    candle = _candle(context)

    candle.y_axis = dcg.Axis.Y3

    assert candle.axes == (dcg.Axis.X1, dcg.Axis.Y3)
    assert candle._volume_bar_series.axes == (dcg.Axis.X1, dcg.Axis.Y3)


def test_candle_rejects_invalid_or_conflicting_axes(context):
    with pytest.raises(ValueError, match="y_axis must be"):
        _candle(context, y_axis=dcg.Axis.X1)
    with pytest.raises(ValueError, match="axes cannot be supplied with y_axis"):
        _candle(context, axes=(dcg.Axis.X1, dcg.Axis.Y2))
    with pytest.raises(ValueError, match="volume_kwargs cannot contain axes"):
        _candle(context, volume_kwargs={"axes": (dcg.Axis.X1, dcg.Axis.Y2)})