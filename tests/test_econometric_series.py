import numpy as np
import pytest

import dearcygui as dcg

from dearcyfi import PlotEconometricSeries
from dearcyfi.econometric_series import _DrawnHoverCondition


@pytest.fixture
def context():
    return dcg.Context()


def _children(series, kind):
    return [child for child in series.children if isinstance(child, kind)]


def _polyline_points(series):
    return [[tuple(point) for point in line.points] for line in _children(series, dcg.DrawPolyline)]


def _button_points(series):
    return [tuple(button.p1) for button in _children(series, dcg.DrawInvisibleButton)]


def test_series_is_one_legend_enabled_plot_item(context):
    series = PlotEconometricSeries(context, dates=[1, 2], values=[3, 4], markers=True, label="CPI")

    assert isinstance(series, dcg.DrawInPlot)
    assert series.no_legend is False
    assert series.label == "CPI"
    assert all(child.parent is series for child in series.children)


def test_rejects_mismatched_timestamp_and_value_lengths(context):
    with pytest.raises(ValueError, match="same length"):
        PlotEconometricSeries(context, dates=[1, 2], values=[3])


def test_line_breaks_at_non_finite_observations_without_interpolating(context):
    series = PlotEconometricSeries(
        context,
        dates=[1, 2, 3, 4, 5, np.nan, 7],
        values=[10, 20, np.nan, 40, 50, 60, 70],
        tooltip=False,
    )

    np.testing.assert_equal(series.values, [10, 20, np.nan, 40, 50, 60, 70])
    assert _polyline_points(series) == [[(1, 10), (2, 20)], [(4, 40), (5, 50)]]
    anchors = _children(series, dcg.DrawCircle)
    assert [tuple(anchor.center) for anchor in anchors] == [(7, 70)]
    assert anchors[0].radius == 0


def test_markers_tooltips_and_styles_use_screen_space_primitives(context):
    series = PlotEconometricSeries(
        context,
        dates=[1, 2, 4],
        values=[10, np.nan, 40],
        markers=True,
        line_color=(1, 2, 3, 255),
        line_thickness=2.5,
        marker_color=(4, 5, 6, 255),
        marker_radius=4,
    )

    markers = _children(series, dcg.DrawCircle)
    assert [tuple(marker.center) for marker in markers] == [(1, 10), (4, 40)]
    assert all(marker.radius == -4 for marker in markers)
    assert markers[0].fill == pytest.approx([4 / 255, 5 / 255, 6 / 255, 1.0])
    assert _children(series, dcg.DrawPolyline) == []
    assert _button_points(series) == [(1, 10), (4, 40)]

    series.update_all(dates=[1, 2], values=[10, 20])
    line = _children(series, dcg.DrawPolyline)[0]
    assert line.thickness == -2.5
    assert line.color == pytest.approx([1 / 255, 2 / 255, 3 / 255, 1.0])


def test_disabled_tooltips_create_no_hit_regions(context):
    series = PlotEconometricSeries(context, dates=[1, 2], values=[3, 4], tooltip=False)

    assert _children(series, dcg.DrawInvisibleButton) == []


def test_empty_and_non_finite_data_create_no_primitives(context):
    series = PlotEconometricSeries(context, dates=[], values=[], markers=True)
    assert series.children == []

    series.update_all(dates=[1, 2], values=[np.nan, np.inf])
    assert series.children == []


def test_tooltip_reports_source_date_after_collapse(context):
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
    assert _button_points(series) == [(5, 1), (6, 2)]
    assert [button.user_data for button in _children(series, dcg.DrawInvisibleButton)] == [
        (100, 1),
        (200, 2),
    ]
    assert [tuple(marker.center) for marker in _children(series, dcg.DrawCircle)] == [(5, 1), (6, 2)]

    series.restore_source_dates()
    np.testing.assert_array_equal(series.plot_dates, [100, 200])
    assert _polyline_points(series) == [[(100, 1), (200, 2)]]


def test_invalid_complete_update_does_not_mutate_existing_data(context):
    series = PlotEconometricSeries(context, dates=[10, 20], values=[1, 2])
    children = list(series.children)

    with pytest.raises(ValueError, match="same length"):
        series.update_all(dates=[30], values=[3, 4])

    np.testing.assert_array_equal(series.source_dates, [10, 20])
    np.testing.assert_array_equal(series.values, [1, 2])
    assert series.children == children


def test_complete_update_replaces_primitives_and_keeps_visibility(context):
    series = PlotEconometricSeries(context, dates=[10, 20], values=[1, 2], show=False)
    series._active_tooltip = dcg.Tooltip(context)
    series._active_tooltip_target = _children(series, dcg.DrawInvisibleButton)[0]

    series.update_all(dates=[30, 40, 50], values=[3, 4, 5], label="GDP")

    assert series.label == "GDP"
    assert series.show is False
    assert _polyline_points(series) == [[(30, 3), (40, 4), (50, 5)]]
    assert _button_points(series) == [(30, 3), (40, 4), (50, 5)]
    assert series._active_tooltip is None


def test_tooltip_condition_requires_target_drawn_each_frame(context):
    class HoveredTarget:
        class state:
            hovered = True

    condition = _DrawnHoverCondition(context)
    target = HoveredTarget()

    assert condition.check_status(target) is False
    condition.run(target)
    assert condition.check_status(target) is True
    # A legend-hidden target is not drawn, so its stale hover state is ignored.
    assert condition.check_status(target) is False


@pytest.mark.parametrize("y_axis", [dcg.Axis.Y1, dcg.Axis.Y2, dcg.Axis.Y3])
def test_y_axis_selects_series_axes(context, y_axis):
    series = PlotEconometricSeries(context, dates=[10, 20], values=[1, 2], y_axis=y_axis)

    assert series.y_axis == y_axis
    assert series.axes == (dcg.Axis.X1, y_axis)
    series.set_plot_dates([5, 6])
    assert series.axes == (dcg.Axis.X1, y_axis)


def test_econometric_y_axis_defaults_to_y1(context):
    series = PlotEconometricSeries(context, dates=[10], values=[1])

    assert series.y_axis == dcg.Axis.Y1
    assert series.axes == (dcg.Axis.X1, dcg.Axis.Y1)


def test_econometric_rejects_invalid_or_conflicting_axes(context):
    with pytest.raises(ValueError, match="y_axis must be"):
        PlotEconometricSeries(context, dates=[10], values=[1], y_axis=dcg.Axis.X1)
    with pytest.raises(ValueError, match="use y_axis"):
        PlotEconometricSeries(context, dates=[10], values=[1], axes=(dcg.Axis.X1, dcg.Axis.Y2))


@pytest.mark.parametrize("option", ["line_kwargs", "marker_kwargs"])
def test_rejects_legacy_native_kwargs(context, option):
    with pytest.raises(ValueError, match=f"{option} is no longer supported.*line_color"):
        PlotEconometricSeries(context, dates=[10], values=[1], **{option: {}})


@pytest.mark.parametrize("option", ["line_thickness", "marker_radius"])
@pytest.mark.parametrize("value", [0, -1, np.nan])
def test_rejects_invalid_screen_sizes(context, option, value):
    with pytest.raises(ValueError, match=option):
        PlotEconometricSeries(context, dates=[10], values=[1], **{option: value})
