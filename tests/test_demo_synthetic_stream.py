import importlib.util
from pathlib import Path

import pytest


_STREAM_PATH = (
    Path(__file__).parents[1]
    / "examples"
    / "DearCyFi_Demo"
    / "synthetic_candle_stream.py"
)
_SPEC = importlib.util.spec_from_file_location("dearcyfi_demo_synthetic_stream", _STREAM_PATH)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
SyntheticCandleStream = _MODULE.SyntheticCandleStream


def _next(feed, timestamp=1_700_000_000.0):
    return feed.next_event(
        timestamp=timestamp,
        high=12.0,
        low=9.0,
        close=11.0,
        volume=100.0,
    )


def test_synthetic_stream_revisions_and_appends_are_deterministic_and_valid():
    first = SyntheticCandleStream(interval=300.0, seed=19)
    second = SyntheticCandleStream(interval=300.0, seed=19)

    events = [_next(first) for _ in range(4)]
    assert events == [_next(second) for _ in range(4)]
    assert [event[0] for event in events] == ["update", "update", "update", "append"]
    assert all(event[1] == 1_700_000_000.0 for event in events[:3])
    assert events[3][1] == 1_700_000_300.0
    for event_type, _timestamp, values in events:
        assert values["volume"] >= 0.0
        if event_type == "append":
            assert values["low"] <= values["open"] <= values["high"]
            assert values["low"] <= values["close"] <= values["high"]
        else:
            assert values["low"] <= 10.0 <= values["high"]
            assert values["low"] <= values["close"] <= values["high"]


def test_synthetic_stream_gap_is_applied_to_the_next_append_once():
    feed = SyntheticCandleStream(interval=300.0, seed=7)
    for _ in range(3):
        assert _next(feed)[0] == "update"
    feed.gap_next = True

    event_type, timestamp, _values = _next(feed)
    assert event_type == "append"
    assert timestamp == 1_700_000_750.0
    assert feed.gap_next is False

    assert _next(feed)[0] == "update"


@pytest.mark.parametrize("interval", [0.0, -1.0, float("nan")])
def test_synthetic_stream_rejects_invalid_interval(interval):
    with pytest.raises(ValueError, match="interval"):
        SyntheticCandleStream(interval=interval, seed=1)
