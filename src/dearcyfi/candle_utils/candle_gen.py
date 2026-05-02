import numpy as np
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


def _apply_weekend_gaps(dates):
    """Shift timestamps forward at weekend boundaries to preserve a continuous trading index."""
    dates = dates.copy()
    weekdays = np.array([
        datetime.fromtimestamp(ts, tz=timezone.utc).weekday() for ts in dates
    ])

    # Weekend starts are rising edges into Saturday/Sunday.
    weekend_starts = np.where((weekdays[:-1] < 5) & (weekdays[1:] >= 5))[0] + 1
    for start_idx in weekend_starts:
        dates[start_idx:] += 2 * 86400  # Shift by 2 days in seconds.

    return dates

def generate_fake_candlestick_data(
    dates=None,
    base_price=150.0,
    volatility=0.02,
    seed=42,
    remove_weekends=True,
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
    remove_weekends : bool
        If True, remove entries that fall on Saturday or Sunday.
    length : int
        Number of intervals to generate if dates is None.
    start_date : str
        Start date in 'YYYY-MM-DD' format (used if dates is None).
    interval : str
        "daily", "hourly", or "minute" candles.

    Returns
    -------
    dates : np.ndarray
    opens : np.ndarray
    highs : np.ndarray
    lows : np.ndarray
    closes : np.ndarray
    """


    # Determine interval in seconds
    if interval == "daily":
        step = 86400
    elif interval == "hourly":
        step = 3600
    elif interval == "minute":
        step = 60
    else:
        raise ValueError("interval must be 'daily', 'hourly', or 'minute'")

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

    if remove_weekends:
        dates = _apply_weekend_gaps(dates)

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