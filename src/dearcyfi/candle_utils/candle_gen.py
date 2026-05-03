import numpy as np
import warnings
from datetime import datetime, timezone


def _create_candles_and_volume(dates, base_price, volatility, seed, random):
    """Create OHLC candles and volume series for the provided timestamps."""
    if not random:
        np.random.seed(seed)

    changes = np.random.normal(0.001, volatility, len(dates))
    changes += 0.002  # Upward trend

    closes = np.zeros(len(dates))
    closes[0] = base_price
    for i in range(1, len(dates)):
        closes[i] = closes[i - 1] * (1 + changes[i])

    opens = np.zeros(len(dates))
    highs = np.zeros(len(dates))
    lows = np.zeros(len(dates))

    for i in range(len(dates)):
        if i == 0:
            opens[i] = base_price * (1 - volatility / 2)
        else:
            opens[i] = closes[i - 1] * (1 + np.random.normal(0, volatility / 2))
        highs[i] = max(opens[i], closes[i]) * (1 + abs(np.random.normal(0, volatility)))
        lows[i] = min(opens[i], closes[i]) * (1 - abs(np.random.normal(0, volatility)))

    if not random:
        np.random.seed(seed + 1)  # Different seed for volume

    volume = np.random.uniform(1, 20, len(dates))
    volume = np.clip(volume, 0, None)  # Ensure no negative volumes

    return opens, highs, lows, closes, volume


def _apply_gaps(dates, gap_types):
    """Shift timestamps to introduce the requested market-closure gaps."""
    dates = dates.copy()

    if isinstance(gap_types, str):
        gap_types = [gap_types]

    normalized_gap_types = []
    for gap_type in gap_types:
        normalized_gap_type = gap_type.strip().lower()
        if normalized_gap_type == "weekends":
            normalized_gap_type = "weekend"
        normalized_gap_types.append(normalized_gap_type)

    invalid_gap_types = sorted(set(normalized_gap_types) - {"weekend", "overnight"})
    if invalid_gap_types:
        raise ValueError(
            "gap_types must contain only 'weekend', 'weekends', or 'overnight'"
        )

    if len(dates) < 2:
        return dates

    # Compress each intraday session so the next session opens after an overnight gap.
    if "overnight" in normalized_gap_types:
        step = int(np.median(np.diff(dates))) # step is the median interval between timestamps in seconds
        if step < 86400: # see if the step is less than a day, otherwise we can't apply overnight gaps
            trading_session_seconds = int(6.5 * 3600)  #3600 seconds per hour * 6.5 hours in a trading day
            bars_per_session = max(1, int(np.ceil(trading_session_seconds / step))) # Calculate how many bars fit in a trading session
            overnight_gap_seconds = 86400 - (bars_per_session * step) # Calculate the gap needed to shift the next session to the next day

            if overnight_gap_seconds > 0:
                overnight_starts = np.arange(bars_per_session, len(dates), bars_per_session)
                for start_idx in overnight_starts:
                    dates[start_idx:] += overnight_gap_seconds

    # Weekend starts are rising edges into Saturday/Sunday.
    if "weekend" in normalized_gap_types:
        shifted_dates = dates.copy()
        weekend_offset = 0
        previous_weekday = datetime.fromtimestamp(
            shifted_dates[0], tz=timezone.utc
        ).weekday()

        for index in range(1, len(shifted_dates)):
            shifted_dates[index] = dates[index] + weekend_offset
            current_weekday = datetime.fromtimestamp(
                shifted_dates[index], tz=timezone.utc
            ).weekday()

            if previous_weekday < 5 and current_weekday >= 5:
                weekend_offset += 2 * 86400
                shifted_dates[index] = dates[index] + weekend_offset
                current_weekday = datetime.fromtimestamp(
                    shifted_dates[index], tz=timezone.utc
                ).weekday()

            previous_weekday = current_weekday

        dates = shifted_dates

    return dates


def _interval_to_seconds(interval):
    """Map supported interval aliases to their duration in seconds."""
    interval_map = {
        "weekly": 7 * 86400,
        "daily": 86400,
        "hourly": 3600,
        "15min": 15 * 60,
        "5min": 5 * 60,
        "minute": 60,
    }

    try:
        return interval_map[interval]
    except KeyError as exc:
        raise ValueError(
            "interval must be 'weekly', 'daily', 'hourly', '15min', '5min', or 'minute'"
        ) from exc


def _start_date_to_timestamp(start_date):
    """Normalize supported start_date inputs to a UTC Unix timestamp."""
    if isinstance(start_date, (int, float)):
        return int(start_date)

    if isinstance(start_date, datetime):
        return int(start_date.replace(tzinfo=timezone.utc).timestamp())

    normalized_start_date = str(start_date).strip()
    supported_formats = (
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%dT%H:%M:%S",
    )
    for date_format in supported_formats:
        try:
            parsed_start_date = datetime.strptime(normalized_start_date, date_format)
            return int(parsed_start_date.replace(tzinfo=timezone.utc).timestamp())
        except ValueError:
            continue

    raise ValueError(
        "start_date must be a Unix timestamp, datetime, or a string in "
        "'YYYY-MM-DD', 'YYYY-MM-DD HH:MM', 'YYYY-MM-DD HH:MM:SS', "
        "'YYYY-MM-DDTHH:MM', or 'YYYY-MM-DDTHH:MM:SS' format"
    )

def generate_fake_candlestick_data(
    dates=None,
    base_price=150.0,
    volatility=0.02,
    seed=42,
    gap_types=None,
    length=30,
    start_date="2024-08-05",
    random=False,
    interval="daily"  # New kwarg: "daily", "hourly", or "minute"
):
    """
    Generate fake OHLC (Open, High, Low, Close) stock data for candlestick charts,
    optionally removing entries that fall on weekends.

    Parameters
    ----------
    dates : np.ndarray or None
        Array of UNIX timestamps. If None, generates sequential intervals starting from start_date.
    base_price : float
        Starting price for the stock.
    volatility : float
        Standard deviation of returns.
    seed : int
        Random seed for reproducibility.
    gap_types : list[str] or None
        Gap types to apply. Supported values are "weekend"/"weekends" and "overnight".
        When omitted, no gaps are applied and a warning is emitted.
    length : int
        Number of intervals to generate if dates is None.
    start_date : str | int | float | datetime
        Start date as a 'YYYY-MM-DD' string, a UNIX timestamp (int/float),
        a datetime object, or a datetime string such as 'YYYY-MM-DD HH:MM'
        (used if dates is None).
    interval : str
        "weekly", "daily", "hourly", "15min", "5min", or "minute" candles.

    Returns
    -------
    dates : np.ndarray
    opens : np.ndarray
    highs : np.ndarray
    lows : np.ndarray
    closes : np.ndarray
    """

    interval = str(interval).strip().lower()
    step = _interval_to_seconds(interval)

    if dates is None:
        start = _start_date_to_timestamp(start_date)
        dates = np.array([start + step * i for i in range(length)])

    opens, highs, lows, closes, volume = _create_candles_and_volume(
        dates=dates,
        base_price=base_price,
        volatility=volatility,
        seed=seed,
        random=random,
    )

    if gap_types is None:
        warnings.warn(
            "No gap_types specified; no gaps will be applied. "
            "Pass gap_types=['weekend'] or ['overnight'] to enable gaps.",
            stacklevel=2,
        )
        gap_types = []

    if interval == "weekly" and gap_types:
        warnings.warn(
            "Weekly candles do not support weekend or overnight gaps; requested gaps will be ignored.",
            stacklevel=2,
        )
        gap_types = []

    if gap_types:
        dates = _apply_gaps(dates, gap_types)

    # Add a continuous index column
    index = np.arange(len(dates))

    return dates, opens, highs, lows, closes, index, volume

if __name__ == "__main__":
    from datetime import datetime, timezone

    ref_str = "2024-08-05"
    ref_dt  = datetime(2024, 8, 5, tzinfo=timezone.utc)
    ref_ts  = int(ref_dt.timestamp())  # 1722816000

    print(f"Reference timestamp: {ref_ts}  ({ref_str})\n")

    # --- start_date input types all produce the same first timestamp ---
    dates_str, *_ = generate_fake_candlestick_data(
        start_date=ref_str, length=3, gap_types=[], interval="daily"
    )
    dates_int, *_ = generate_fake_candlestick_data(
        start_date=ref_ts, length=3, gap_types=[], interval="daily"
    )
    dates_dt, *_ = generate_fake_candlestick_data(
        start_date=ref_dt, length=3, gap_types=[], interval="daily"
    )
    assert dates_str[0] == dates_int[0] == dates_dt[0], (
        f"start_date type mismatch: str={dates_str[0]}, int={dates_int[0]}, dt={dates_dt[0]}"
    )
    print(f"str/int/datetime start_date -> same timestamp {dates_str[0]}  ✓")

    # --- output arrays all have the requested length ---
    N = 50
    result = generate_fake_candlestick_data(start_date=ref_str, length=N, gap_types=[], interval="hourly")
    dates_out, opens_out, highs_out, lows_out, closes_out, index_out, volume_out = result
    for name, arr in zip(
        ("dates", "opens", "highs", "lows", "closes", "index", "volume"),
        result,
    ):
        assert len(arr) == N, f"{name}: expected {N} elements, got {len(arr)}"
    print(f"All output arrays have length {N}  ✓")

    # --- interval step sizes ---
    interval_steps = {
        "weekly": 7 * 86400,
        "daily":  86400,
        "hourly": 3600,
        "15min":  15 * 60,
        "5min":   5 * 60,
        "minute": 60,
    }
    for iv, expected_step in interval_steps.items():
        d, *_ = generate_fake_candlestick_data(
            start_date=ref_str, length=5, gap_types=[], interval=iv
        )
        actual_step = int(d[1] - d[0])
        assert actual_step == expected_step, (
            f"interval '{iv}': expected step {expected_step}s, got {actual_step}s"
        )
        print(f"interval '{iv}' step = {expected_step}s  ✓")

    # --- weekend gap removes Sat/Sun from output ---
    dates_wknd, *_ = generate_fake_candlestick_data(
        start_date=ref_str, length=14, gap_types=["weekend"], interval="daily"
    )
    weekdays = [datetime.fromtimestamp(ts, tz=timezone.utc).weekday() for ts in dates_wknd]
    assert all(wd < 5 for wd in weekdays), f"Weekend gap left Sat/Sun in output: {weekdays}"
    print("Weekend gap: no Sat/Sun in output  ✓")

    # --- pre-built dates array bypasses start_date ---
    custom_dates = np.array([1_000_000, 1_000_060, 1_000_120], dtype=np.float64)
    d_passthrough, *_ = generate_fake_candlestick_data(
        dates=custom_dates, gap_types=[], start_date="1999-01-01"
    )
    assert np.array_equal(d_passthrough, custom_dates), "Pre-built dates array was not passed through unchanged"
    print("Pre-built dates passthrough  ✓")

    # --- invalid gap_type raises ValueError ---
    try:
        generate_fake_candlestick_data(start_date=ref_str, gap_types=["bogus"], length=5)
        assert False, "Expected ValueError for invalid gap_type"
    except ValueError:
        print("Invalid gap_type raises ValueError  ✓")

    # --- invalid interval raises ValueError ---
    try:
        generate_fake_candlestick_data(start_date=ref_str, gap_types=[], interval="monthly", length=5)
        assert False, "Expected ValueError for invalid interval"
    except ValueError:
        print("Invalid interval raises ValueError  ✓")

    print("\nAll tests passed. ✓")