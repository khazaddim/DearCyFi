"""Pytest notes for this file.

Run the whole file:
    python -m pytest tests/test_candle_gen.py

Run with verbose per-test output:
    python -m pytest tests/test_candle_gen.py -vv

Run only tests whose names match a keyword:
    python -m pytest tests/test_candle_gen.py -k interval -vv

Stop on the first failure:
    python -m pytest tests/test_candle_gen.py -x

Run a single test function:
    python -m pytest tests/test_candle_gen.py -k test_interval_step_sizes -vv
"""

from datetime import datetime, timezone

import numpy as np
import pytest

from dearcyfi.candle_utils.candle_gen import generate_fake_candlestick_data
from dearcyfi.candle_utils.gap_utils import GapCollapseManager


REFERENCE_DATE_STR = "2024-08-05"
REFERENCE_DATE_DT = datetime(2024, 8, 5, tzinfo=timezone.utc)
REFERENCE_DATE_TS = int(REFERENCE_DATE_DT.timestamp())
REFERENCE_DATETIME_STR = "2024-08-05 09:30"
REFERENCE_DATETIME_DT = datetime(2024, 8, 5, 9, 30, tzinfo=timezone.utc)
REFERENCE_DATETIME_TS = int(REFERENCE_DATETIME_DT.timestamp())


def test_start_date_overloads_produce_same_first_timestamp():
    dates_str, *_ = generate_fake_candlestick_data(
        start_date=REFERENCE_DATE_STR,
        length=3,
        gap_types=[],
        interval="daily",
    )
    dates_int, *_ = generate_fake_candlestick_data(
        start_date=REFERENCE_DATE_TS,
        length=3,
        gap_types=[],
        interval="daily",
    )
    dates_dt, *_ = generate_fake_candlestick_data(
        start_date=REFERENCE_DATE_DT,
        length=3,
        gap_types=[],
        interval="daily",
    )

    assert dates_str[0] == dates_int[0] == dates_dt[0]


def test_timed_start_date_overloads_produce_same_first_timestamp():
    dates_str, *_ = generate_fake_candlestick_data(
        start_date=REFERENCE_DATETIME_STR,
        length=3,
        gap_types=[],
        interval="hourly",
    )
    dates_int, *_ = generate_fake_candlestick_data(
        start_date=REFERENCE_DATETIME_TS,
        length=3,
        gap_types=[],
        interval="hourly",
    )
    dates_dt, *_ = generate_fake_candlestick_data(
        start_date=REFERENCE_DATETIME_DT,
        length=3,
        gap_types=[],
        interval="hourly",
    )

    assert dates_str[0] == dates_int[0] == dates_dt[0]


def test_all_output_arrays_have_requested_length():
    length = 50
    result = generate_fake_candlestick_data(
        start_date=REFERENCE_DATE_STR,
        length=length,
        gap_types=[],
        interval="hourly",
    )

    for output in result:
        assert len(output) == length


@pytest.mark.parametrize(
    ("interval", "expected_step"),
    [
        ("weekly", 7 * 86400),
        ("daily", 86400),
        ("hourly", 3600),
        ("15min", 15 * 60),
        ("5min", 5 * 60),
        ("minute", 60),
    ],
)
def test_interval_step_sizes(interval, expected_step):
    dates, *_ = generate_fake_candlestick_data(
        start_date=REFERENCE_DATE_STR,
        length=5,
        gap_types=[],
        interval=interval,
    )

    assert int(dates[1] - dates[0]) == expected_step


def test_weekend_gap_daily_output_contains_no_weekend_dates():
    dates, *_ = generate_fake_candlestick_data(
        start_date=REFERENCE_DATE_STR,
        length=30,
        gap_types=["weekend"],
        interval="daily",
    )

    weekdays = [
        datetime.fromtimestamp(timestamp, tz=timezone.utc).weekday()
        for timestamp in dates
    ]

    assert all(weekday < 5 for weekday in weekdays)


def test_weekend_gap_daily_output_is_unique_and_increasing():
    dates, *_ = generate_fake_candlestick_data(
        start_date=REFERENCE_DATE_STR,
        length=60,
        gap_types=["weekend"],
        interval="daily",
    )

    assert np.all(np.diff(dates) > 0)
    assert np.unique(dates).size == dates.size


def test_weekend_gap_daily_collapse_outputs_are_unique():
    dates, *_ = generate_fake_candlestick_data(
        start_date=REFERENCE_DATE_STR,
        length=60,
        gap_types=["weekend"],
        interval="daily",
    )

    manager = GapCollapseManager()
    collapsed_dates = manager.collapse_dates(dates, use_local_time=False, debug=False)

    vectorized_manager = GapCollapseManager()
    vectorized_dates = vectorized_manager.collapse_dates_vectorized(
        dates,
        use_local_time=False,
        debug=False,
    )

    assert np.unique(collapsed_dates).size == collapsed_dates.size
    assert np.unique(vectorized_dates).size == vectorized_dates.size
    np.testing.assert_array_equal(vectorized_dates, collapsed_dates)


def test_prebuilt_dates_bypass_start_date_generation():
    custom_dates = np.array([1_000_000, 1_000_060, 1_000_120], dtype=np.float64)

    dates, *_ = generate_fake_candlestick_data(
        dates=custom_dates,
        gap_types=[],
        start_date="1999-01-01",
    )

    assert np.array_equal(dates, custom_dates)


def test_invalid_gap_type_raises_value_error():
    with pytest.raises(ValueError, match="gap_types"):
        generate_fake_candlestick_data(
            start_date=REFERENCE_DATE_STR,
            gap_types=["bogus"],
            length=5,
        )


def test_invalid_interval_raises_value_error():
    with pytest.raises(ValueError, match="interval"):
        generate_fake_candlestick_data(
            start_date=REFERENCE_DATE_STR,
            gap_types=[],
            interval="monthly",
            length=5,
        )