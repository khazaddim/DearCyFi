import numpy as np
import pytest

import dearcygui as dcg

from dearcyfi import PlotEconometricSeries


@pytest.fixture
def context():
    return dcg.Context()


def test_rejects_mismatched_timestamp_and_value_lengths(context):
    with pytest.raises(ValueError, match="same length"):
        PlotEconometricSeries(context, dates=[1, 2], values=[3])


def test_preserves_nan_and_disables_line_skipping_by_default(context):
    series = PlotEconometricSeries(context, dates=[1, 2, 3], values=[4, np.nan, 6])

    np.testing.assert_equal(series.values, np.array([4.0, np.nan, 6.0]))
    assert series.line.skip_nan is False


def test_plot_date_updates_preserve_and_restore_source_dates(context):
    series = PlotEconometricSeries(
        context,
        dates=[10, 20],
        source_dates=[100, 200],
        values=[1, 2],
        markers=True,
    )

    series.set_plot_dates([5, 6])
    np.testing.assert_array_equal(series.plot_dates, [5, 6])
    np.testing.assert_array_equal(series.source_dates, [100, 200])
    np.testing.assert_array_equal(series.line.X, [5, 6])
    np.testing.assert_array_equal(series.markers.X, [5, 6])

    series.restore_source_dates()
    np.testing.assert_array_equal(series.plot_dates, [100, 200])


def test_invalid_complete_update_does_not_mutate_existing_data(context):
    series = PlotEconometricSeries(context, dates=[10, 20], values=[1, 2])

    with pytest.raises(ValueError, match="same length"):
        series.update_all(dates=[30], values=[3, 4])

    np.testing.assert_array_equal(series.source_dates, [10, 20])
    np.testing.assert_array_equal(series.values, [1, 2])


def test_complete_update_replaces_render_and_interaction_data(context):
    series = PlotEconometricSeries(context, dates=[10, 20], values=[1, 2], tooltip=True)

    series.update_all(dates=[30], values=[3], label="GDP")

    np.testing.assert_array_equal(series.line.X, [30])
    np.testing.assert_array_equal(series.line.Y, [3])
    assert series.line.label == "GDP"
    assert len(series._interaction_layer.children) == 1


@pytest.mark.parametrize("y_axis", [dcg.Axis.Y1, dcg.Axis.Y2, dcg.Axis.Y3])
def test_y_axis_propagates_to_all_econometric_elements(context, y_axis):
    series = PlotEconometricSeries(
        context,
        dates=[10, 20],
        values=[1, 2],
        markers=True,
        y_axis=y_axis,
    )

    expected_axes = (dcg.Axis.X1, y_axis)
    assert series.y_axis == y_axis
    assert series.line.axes == expected_axes
    assert series.markers.axes == expected_axes
    assert series._interaction_layer.axes == expected_axes

    series.set_plot_dates([5, 6])
    assert series.line.axes == expected_axes
    assert series.markers.axes == expected_axes
    assert series._interaction_layer.axes == expected_axes


def test_econometric_y_axis_defaults_to_y1(context):
    series = PlotEconometricSeries(context, dates=[10], values=[1])

    assert series.y_axis == dcg.Axis.Y1
    assert series.line.axes == (dcg.Axis.X1, dcg.Axis.Y1)
    assert series._interaction_layer.axes == (dcg.Axis.X1, dcg.Axis.Y1)


def test_econometric_rejects_invalid_or_conflicting_axes(context):
    with pytest.raises(ValueError, match="y_axis must be"):
        PlotEconometricSeries(context, dates=[10], values=[1], y_axis=dcg.Axis.X1)
    with pytest.raises(ValueError, match="line_kwargs cannot contain axes"):
        PlotEconometricSeries(
            context,
            dates=[10],
            values=[1],
            line_kwargs={"axes": (dcg.Axis.X1, dcg.Axis.Y2)},
        )
    with pytest.raises(ValueError, match="marker_kwargs cannot contain axes"):
        PlotEconometricSeries(
            context,
            dates=[10],
            values=[1],
            marker_kwargs={"axes": (dcg.Axis.X1, dcg.Axis.Y2)},
        )