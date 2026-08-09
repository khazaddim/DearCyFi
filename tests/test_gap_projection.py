import numpy as np
import pytest

from dearcyfi.candle_utils.gap_utils import GapCollapsedTimeMap


@pytest.fixture
def time_map() -> GapCollapsedTimeMap:
    source = np.array([0.0, 10.0, 20.0, 100.0, 110.0])
    return GapCollapsedTimeMap.from_real_series(source, use_local_time=False)


def test_project_retained_source_and_boundary_timestamps(time_map):
    values = np.array([0.0, 10.0, 20.0, 100.0, 110.0])

    np.testing.assert_array_equal(
        time_map.project_many(values),
        np.array([0.0, 10.0, 20.0, 30.0, 40.0]),
    )


@pytest.mark.parametrize(
    ("policy", "expected"),
    [("next", 30.0), ("previous", 20.0)],
)
def test_project_timestamp_inside_removed_gap(time_map, policy, expected):
    assert time_map.project(50.0, in_gap=policy) == expected


def test_project_preserves_offsets_outside_source_range(time_map):
    assert time_map.project(-15.0) == -15.0
    assert time_map.project(125.0) == 55.0


def test_project_many_preserves_shape_and_non_finite_values(time_map):
    values = np.array([[10.0, 50.0], [125.0, np.nan]])
    projected = time_map.project_many(values, in_gap="previous")

    assert projected.shape == values.shape
    np.testing.assert_equal(projected, np.array([[10.0, 20.0], [55.0, np.nan]]))


def test_project_rejects_unknown_in_gap_policy(time_map):
    with pytest.raises(ValueError, match="in_gap"):
        time_map.project(50.0, in_gap="nearest")