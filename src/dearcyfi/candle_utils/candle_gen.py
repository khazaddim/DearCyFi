import numpy as np
import warnings
from datetime import datetime, timezone


def _create_candles_and_volume(dates, base_price, volatility, seed, random):
    """Create OHLC candles and volume series for the provided timestamps."""
    print(f"Generating candles with base_price={base_price}, volatility={volatility}, seed={seed}, random={random}")
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
        weekdays = np.array([
            datetime.fromtimestamp(ts, tz=timezone.utc).weekday() for ts in dates
        ])
        weekend_starts = np.where((weekdays[:-1] < 5) & (weekdays[1:] >= 5))[0] + 1
        for start_idx in weekend_starts:
            dates[start_idx:] += 2 * 86400  # Shift by 2 days in seconds.

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
    start_date : str
        Start date in 'YYYY-MM-DD' format (used if dates is None).
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
        # Parse the start_date string to a datetime object
        dt = datetime.strptime(start_date, "%Y-%m-%d")
        start = int(dt.replace(tzinfo=timezone.utc).timestamp())
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
    # Example usage of the function
    dates, opens, highs, lows, closes, index, volume = generate_fake_candlestick_data()
    print("Dates:", dates)
    print("Opens:", opens)
    print("Highs:", highs)
    print("Lows:", lows)
    print("Closes:", closes)
    print("Index:", index)
    print("Volume:", volume)