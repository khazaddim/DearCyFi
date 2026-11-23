"""Shared timestamp validation and cadence helpers for incremental updates."""

import math
from collections.abc import Sized

import numpy as np


def finite_timestamp(value: object, *, name: str = "timestamp") -> float:
    try:
        timestamp = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a finite Unix timestamp in seconds") from exc
    if not math.isfinite(timestamp):
        raise ValueError(f"{name} must be a finite Unix timestamp in seconds")
    return timestamp


def infer_cadence(timestamps: Sized) -> float:
    values = np.asarray(timestamps, dtype=float)
    if values.ndim != 1 or values.size < 2:
        raise ValueError("Streaming cadence requires at least two finite increasing timestamps")
    if not np.all(np.isfinite(values)) or np.any(np.diff(values) <= 0):
        raise ValueError("Streaming cadence requires finite, strictly increasing timestamps")
    cadence = float(np.median(np.diff(values)))
    if not math.isfinite(cadence) or cadence <= 0:
        raise ValueError("Streaming cadence must be finite and positive")
    return cadence


def boundary_tolerance(start: float, timestamp: float, interval: float) -> float:
    end = start + interval
    tolerance = max(
        min(0.001, interval * 1e-6),
        8.0 * max(math.ulp(start), math.ulp(timestamp), math.ulp(end)),
    )
    if tolerance >= interval * 0.5:
        raise ValueError("Timestamp precision is insufficient to distinguish adjacent intervals")
    return tolerance


def latest_interval_matches(start: float, timestamp: float, interval: float) -> bool:
    tolerance = boundary_tolerance(start, timestamp, interval)
    if abs(timestamp - start) <= tolerance:
        timestamp = start
    end = start + interval
    if abs(timestamp - end) <= tolerance:
        timestamp = end
    return start <= timestamp < end


def classify_append_spacing(start: float, timestamp: float, interval: float) -> str:
    tolerance = boundary_tolerance(start, timestamp, interval)
    delta = timestamp - start
    if delta < interval - tolerance:
        return "short"
    if delta <= interval + tolerance:
        return "regular"
    return "gap"
