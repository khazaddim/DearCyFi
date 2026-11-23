import bisect
from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd

from dearcyfi.PyTimeLocator import locator_time3
from dearcyfi.streaming import classify_append_spacing


def _gap_indices(times: np.ndarray, interval: float) -> np.ndarray:
    return np.flatnonzero(
        [
            classify_append_spacing(float(start), float(stop), interval) == "gap"
            for start, stop in zip(times[:-1], times[1:])
        ]
    )


def _median_delta_time(series: pd.Series) -> int | float:
    """Return the median first-difference for an integer-like timestamp series."""
    if not isinstance(series, pd.Series):
        raise ValueError("Input must be a pandas Series.")
    values = series.astype(int)
    deltas = values.diff().dropna()
    return deltas.median()


def _find_large_gaps(series: pd.Series) -> list[dict[str, int]]:
    """Find timestamp deltas larger than the median step."""
    median_delta = _median_delta_time(series)
    if median_delta is None:
        return []

    deltas = series.diff().dropna()
    large_gaps = deltas[deltas > median_delta]
    gaps: list[dict[str, int]] = []
    for idx in large_gaps.index:
        start = int(series.loc[idx - 1])
        stop = int(series.loc[idx])
        duration = stop - start
        gaps.append({"Type": "gap", "start": start, "stop": stop, "duration": duration})
    return gaps


def _chunks(gaps: list[dict[str, int]], start: int, end: int) -> list[dict[str, int]]:
    """Build contiguous chunks between detected gaps."""
    chunk_list: list[dict[str, int]] = []
    if not gaps:
        chunk_list.append({"Type": "chunk", "start": int(start), "stop": int(end), "duration": int(end) - int(start)})
        return chunk_list

    for i in range(len(gaps) + 1):
        if i == 0:
            chunk_list.append(
                {
                    "Type": "chunk",
                    "start": int(start),
                    "stop": int(gaps[i]["start"]),
                    "duration": int(gaps[i]["start"]) - int(start),
                }
            )
        elif i == len(gaps):
            chunk_list.append(
                {
                    "Type": "chunk",
                    "start": int(gaps[i - 1]["stop"]),
                    "stop": int(end),
                    "duration": int(end) - int(gaps[i - 1]["stop"]),
                }
            )
        else:
            chunk_list.append(
                {
                    "Type": "chunk",
                    "start": int(gaps[i - 1]["stop"]),
                    "stop": int(gaps[i]["start"]),
                    "duration": int(gaps[i]["start"]) - int(gaps[i - 1]["stop"]),
                }
            )
    return chunk_list


def find_gaps_and_chunks(series: pd.Series | np.ndarray | Iterable[int]) -> list[dict[str, int]]:
    """
    Find large gaps (based on median delta) and return a single list containing
    both gaps and chunks sorted by start time.
    """
    if isinstance(series, np.ndarray):
        series = pd.Series(series)
    elif not isinstance(series, pd.Series):
        series = pd.Series(list(series))

    series = series.dropna()
    if series.empty:
        return []
    series = series.astype(int).sort_values().reset_index(drop=True)

    gaps = _find_large_gaps(series)
    start = int(series.min())
    end = int(series.max())
    chunk_list = _chunks(gaps, start, end)
    combined = gaps + chunk_list
    combined.sort(key=lambda x: x["start"])
    return combined


@dataclass(frozen=True)
class _TimeSegment:
    # Real-time range [real_start, real_end] maps to collapsed range
    # [collapsed_start, collapsed_end] with slope=1.
    real_start: float
    real_end: float
    collapsed_start: float
    collapsed_end: float
    shift: float  # real = collapsed + shift


@dataclass(frozen=True)
class GapReport:
    gaps: list[dict]
    text: str


class GapCollapsedTimeMap:
    """Piecewise-linear mapping for an axis with arbitrary missing-data gaps.

    The key idea:
    - Within each contiguous data chunk, time is linear (slope 1).
    - Between chunks, we remove the detected gap (delta - base_step) so that
      the first sample after a gap is spaced by ~base_step from the prior sample.

    This makes the mapping robust to weekends + overnights + holidays (or any
    irregular missing-data intervals) as long as they manifest as large deltas
    in the timestamp series.
    """

    def __init__(
        self,
        segments: list[_TimeSegment],
        *,
        day_starts_real: np.ndarray,
        month_starts_real: np.ndarray,
        year_starts_real: np.ndarray,
    ) -> None:
        if not segments:
            raise ValueError("GapCollapsedTimeMap requires at least one segment")
        self._segments = segments
        self._collapsed_starts = [s.collapsed_start for s in segments]
        self._collapsed_ends = [s.collapsed_end for s in segments]
        self._real_starts = [s.real_start for s in segments]

        self._day_starts_real = np.asarray(day_starts_real, dtype=float).tolist()
        self._month_starts_real = np.asarray(month_starts_real, dtype=float).tolist()
        self._year_starts_real = np.asarray(year_starts_real, dtype=float).tolist()

    @property
    def day_starts_real(self) -> np.ndarray:
        return np.asarray(self._day_starts_real, dtype=float)

    @property
    def month_starts_real(self) -> np.ndarray:
        return np.asarray(self._month_starts_real, dtype=float)

    @property
    def year_starts_real(self) -> np.ndarray:
        return np.asarray(self._year_starts_real, dtype=float)

    @staticmethod
    def from_real_series(
        real_times: np.ndarray,
        *,
        use_local_time: bool,
        base_step: float | None = None,
    ) -> "GapCollapsedTimeMap":
        """Create a GapCollapsedTimeMap from a series of real Unix timestamps.

        Automatically detects gaps (e.g., weekends, overnights, holidays) in the time series
        and constructs a piecewise-linear mapping that collapses those gaps while preserving
        one "normal" interval (base_step) between data chunks. This creates a compact timeline
        where missing data doesn't create empty space on the axis.

        The method also derives day, month, and year boundary anchors from the actual data,
        making it robust to irregular missing-data patterns.

        Args:
            real_times: Array of Unix timestamps (seconds since epoch). Must be non-empty
                       and contain finite values. Values will be sorted automatically.
            use_local_time: If True, interpret timestamps in local timezone when deriving
                           day/month/year boundaries. If False, use UTC.
            base_step: Optional stable interval in seconds used to classify gaps.

        Returns:
            GapCollapsedTimeMap: A mapping object that can convert between real timestamps
                                and collapsed (gap-removed) coordinates.

        Raises:
            ValueError: If real_times is empty after filtering for finite values.

        Algorithm:
            1. Filters to finite values and sorts the timestamp array.
            2. Uses the supplied base_step or the median positive delta.
            3. Detects gaps larger than base_step outside numerical tolerance.
            4. For each gap, removes (gap_duration - base_step) from the timeline,
               preserving one normal interval to avoid zero-spacing.
            5. Creates _TimeSegment objects that track the real→collapsed mapping.
            6. Scans the data to find first occurrence of each new day/month/year.

        Example:
            >>> times = np.array([1000, 2000, 3000, 100000, 101000])  # Large gap at 100000
            >>> time_map = GapCollapsedTimeMap.from_real_series(times, use_local_time=True)
            >>> collapsed = time_map.collapse(100500)  # Maps real time to collapsed coordinate
            >>> real = time_map.expand(collapsed)      # Maps back to real time
        """
        times = np.asarray(real_times, dtype=float)
        times = times[np.isfinite(times)]
        if times.size == 0:
            raise ValueError("real_times is empty")
        times = np.sort(times)

        diffs = np.diff(times)
        diffs = diffs[np.isfinite(diffs) & (diffs > 0)]
        if base_step is None:
            base_step = float(np.median(diffs)) if diffs.size else 1.0
        base_step = float(base_step)
        if not np.isfinite(base_step) or base_step <= 0:
            raise ValueError("base_step must be a finite positive interval")

        gap_indices = _gap_indices(times, base_step)

        # Build segments that mirror the collapse behavior, but remove only
        # (gap_delta - base_step) so we preserve one "normal" interval.
        segments: list[_TimeSegment] = []
        cumulative_removed = 0.0
        seg_real_start = float(times[0])

        def _append_segment(real_start: float, real_end: float, removed: float) -> None:
            if real_end < real_start:
                return
            shift = removed
            segments.append(
                _TimeSegment(
                    real_start=real_start,
                    real_end=real_end,
                    collapsed_start=real_start - shift,
                    collapsed_end=real_end - shift,
                    shift=shift,
                )
            )

        for gap_index in gap_indices:
            g_start = float(times[gap_index])
            g_stop = float(times[gap_index + 1])
            remove = max(0.0, g_stop - g_start - base_step)

            # Segment ends at the last sample before the gap.
            _append_segment(seg_real_start, g_start, cumulative_removed)

            cumulative_removed += remove
            seg_real_start = g_stop

        _append_segment(seg_real_start, float(times[-1]), cumulative_removed)

        # Derive boundary anchors from the data itself (robust to missing hours/days):
        # use the first sample of each new day/month/year.
        day_starts: list[float] = []
        month_starts: list[float] = []
        year_starts: list[float] = []

        prev_y = prev_m = prev_d = None
        for ts in times:
            tm = locator_time3.get_time_fields(locator_time3.ImPlotTime.from_double(float(ts)), use_local_time)
            y, m, d = tm.tm_year, tm.tm_mon, tm.tm_mday
            if prev_y is None:
                prev_y, prev_m, prev_d = y, m, d
                day_starts.append(float(ts))
                month_starts.append(float(ts))
                year_starts.append(float(ts))
                continue
            if d != prev_d or m != prev_m or y != prev_y:
                day_starts.append(float(ts))
            if m != prev_m or y != prev_y:
                month_starts.append(float(ts))
            if y != prev_y:
                year_starts.append(float(ts))
            prev_y, prev_m, prev_d = y, m, d

        return GapCollapsedTimeMap(
            segments,
            day_starts_real=np.asarray(day_starts, dtype=float),
            month_starts_real=np.asarray(month_starts, dtype=float),
            year_starts_real=np.asarray(year_starts, dtype=float),
        )

    def project_tail_append(
        self,
        *,
        timestamp: float,
        interval: float,
        spacing: str,
        query: float,
        in_gap: str,
    ) -> float:
        """Project an affected follower through a not-yet-published map tail."""
        previous = self._segments[-1]
        if spacing == "regular":
            return float(query) - previous.shift
        if spacing != "gap" or in_gap not in {"next", "previous"}:
            raise ValueError("spacing must be 'regular' or 'gap'")
        collapsed_start = previous.collapsed_end + interval
        if query < timestamp:
            return collapsed_start if in_gap == "next" else previous.collapsed_end
        return float(query) - (timestamp - collapsed_start)

    def project_tail_append_many(
        self,
        *,
        timestamp: float,
        interval: float,
        spacing: str,
        queries: np.ndarray,
        in_gap: str,
    ) -> np.ndarray:
        values = np.asarray(queries, dtype=float)
        previous = self._segments[-1]
        if spacing == "regular":
            return values - previous.shift
        if spacing != "gap" or in_gap not in {"next", "previous"}:
            raise ValueError("spacing must be 'regular' or 'gap'")
        collapsed_start = previous.collapsed_end + interval
        after_gap = values > timestamp
        projected = np.full(
            values.shape,
            collapsed_start if in_gap == "next" else previous.collapsed_end,
            dtype=float,
        )
        projected[values == timestamp] = collapsed_start
        projected[after_gap] = values[after_gap] - (timestamp - collapsed_start)
        projected[~np.isfinite(values)] = values[~np.isfinite(values)]
        return projected

    def append_source_in_place(
        self,
        previous_timestamp: float,
        timestamp: float,
        *,
        interval: float,
        spacing: str,
        use_local_time: bool,
    ) -> tuple:
        """Extend the map tail and return an O(1) rollback snapshot."""
        timestamp = float(timestamp)
        previous = self._segments[-1]
        if timestamp <= previous.real_end:
            raise ValueError("appended timestamp must be after the current map endpoint")
        previous_fields = locator_time3.get_time_fields(
            locator_time3.ImPlotTime.from_double(previous_timestamp),
            use_local_time,
        )
        current_fields = locator_time3.get_time_fields(
            locator_time3.ImPlotTime.from_double(timestamp),
            use_local_time,
        )
        day_changed = (
            previous_fields.tm_year,
            previous_fields.tm_mon,
            previous_fields.tm_mday,
        ) != (
            current_fields.tm_year,
            current_fields.tm_mon,
            current_fields.tm_mday,
        )
        month_changed = (
            previous_fields.tm_year,
            previous_fields.tm_mon,
        ) != (
            current_fields.tm_year,
            current_fields.tm_mon,
        )
        year_changed = previous_fields.tm_year != current_fields.tm_year
        snapshot = (
            previous,
            len(self._segments),
            len(self._collapsed_starts),
            len(self._collapsed_ends),
            len(self._real_starts),
            len(self._day_starts_real),
            len(self._month_starts_real),
            len(self._year_starts_real),
        )
        if spacing == "regular":
            self._segments[-1] = _TimeSegment(
                real_start=previous.real_start,
                real_end=timestamp,
                collapsed_start=previous.collapsed_start,
                collapsed_end=timestamp - previous.shift,
                shift=previous.shift,
            )
            self._collapsed_ends[-1] = timestamp - previous.shift
        elif spacing == "gap":
            collapsed_start = previous.collapsed_end + interval
            segment = _TimeSegment(
                real_start=timestamp,
                real_end=timestamp,
                collapsed_start=collapsed_start,
                collapsed_end=collapsed_start,
                shift=timestamp - collapsed_start,
            )
            self._segments.append(segment)
            self._collapsed_starts.append(segment.collapsed_start)
            self._collapsed_ends.append(segment.collapsed_end)
            self._real_starts.append(segment.real_start)
        else:
            raise ValueError("spacing must be 'regular' or 'gap'")
        if day_changed and (not self._day_starts_real or self._day_starts_real[-1] != timestamp):
            self._day_starts_real.append(timestamp)
        if month_changed and (not self._month_starts_real or self._month_starts_real[-1] != timestamp):
            self._month_starts_real.append(timestamp)
        if year_changed and (not self._year_starts_real or self._year_starts_real[-1] != timestamp):
            self._year_starts_real.append(timestamp)
        return snapshot

    def rollback_source_append(self, snapshot: tuple) -> None:
        (
            previous_segment,
            segment_count,
            collapsed_start_count,
            collapsed_end_count,
            real_start_count,
            day_count,
            month_count,
            year_count,
        ) = snapshot
        del self._segments[segment_count:]
        del self._collapsed_starts[collapsed_start_count:]
        del self._collapsed_ends[collapsed_end_count:]
        del self._real_starts[real_start_count:]
        self._segments[-1] = previous_segment
        self._collapsed_ends[-1] = previous_segment.collapsed_end
        del self._day_starts_real[day_count:]
        del self._month_starts_real[month_count:]
        del self._year_starts_real[year_count:]

    def expand(self, collapsed_time: float) -> float:
        """Map collapsed-x back to real unix time (seconds)."""
        x = float(collapsed_time)
        i = bisect.bisect_right(self._collapsed_starts, x) - 1
        if i < 0:
            i = 0
        if i >= len(self._segments):
            i = len(self._segments) - 1
        seg = self._segments[i]
        if x < seg.collapsed_start:
            x = seg.collapsed_start
        elif x > seg.collapsed_end:
            x = seg.collapsed_end
        return x + seg.shift

    def collapse(self, real_time: float) -> float:
        """Map real unix time (seconds) to collapsed-x (only well-defined inside segments)."""
        t = float(real_time)
        # Find segment by scanning; segments are few (gaps count) so this is fine.
        for seg in self._segments:
            if seg.real_start <= t <= seg.real_end:
                return t - seg.shift
        # If outside, clamp to nearest edge.
        if t < self._segments[0].real_start:
            return self._segments[0].collapsed_start
        return self._segments[-1].collapsed_end

    def project(self, real_time: float, *, in_gap: str = "next") -> float:
        """Project an arbitrary timestamp through this map.

        Timestamps in retained segments keep their position. Values inside a
        removed gap snap to its next or previous source boundary. Values outside
        the source range retain their offset using the nearest segment's shift.
        """
        if in_gap not in {"next", "previous"}:
            raise ValueError("in_gap must be 'next' or 'previous'")

        timestamp = float(real_time)
        if not np.isfinite(timestamp):
            return timestamp

        first = self._segments[0]
        last = self._segments[-1]
        if timestamp < first.real_start:
            return timestamp - first.shift
        if timestamp > last.real_end:
            return timestamp - last.shift

        index = max(0, bisect.bisect_right(self._real_starts, timestamp) - 1)
        segment = self._segments[index]
        if timestamp <= segment.real_end:
            return timestamp - segment.shift
        if index + 1 < len(self._segments):
            next_segment = self._segments[index + 1]
            if timestamp < next_segment.real_start:
                if in_gap == "next":
                    return next_segment.collapsed_start
                return segment.collapsed_end
        raise ValueError(f"timestamp {timestamp!r} could not be projected")

    def project_many(self, real_times: np.ndarray, *, in_gap: str = "next") -> np.ndarray:
        """Vectorized form of :meth:`project` for follower timestamps."""
        times = np.asarray(real_times, dtype=float)
        flat = times.reshape(-1)
        projected = np.fromiter(
            (self.project(timestamp, in_gap=in_gap) for timestamp in flat),
            dtype=float,
            count=flat.size,
        )
        return projected.reshape(times.shape)

    def debug_dump(self, limit: int = 20) -> str:
        """Print and return a compact view of real<->collapsed segment mapping."""
        lines = [
            f"[GapCollapsedTimeMap] segments={len(self._segments)}",
            (
                f"  boundaries: day={len(self.day_starts_real)} "
                f"month={len(self.month_starts_real)} year={len(self.year_starts_real)}"
            ),
        ]
        max_rows = max(0, int(limit))
        for i, seg in enumerate(self._segments[:max_rows]):
            lines.append(
                f"  [{i:02d}] real=({seg.real_start:.3f} -> {seg.real_end:.3f})  "
                f"collapsed=({seg.collapsed_start:.3f} -> {seg.collapsed_end:.3f})  "
                f"shift={seg.shift:.3f}"
            )
        if len(self._segments) > max_rows:
            lines.append(f"  ... {len(self._segments) - max_rows} more segment(s)")
        out = "\n".join(lines)
        print(out)
        return out


class GapCollapseManager:
    def __init__(self) -> None:
        self.time_is_collapsed = False
        self.time_map: GapCollapsedTimeMap | None = None
        self.dates_real: np.ndarray | None = None
        self.stream_source_id: str | None = None
        self.stream_interval: float | None = None

    @staticmethod
    def _compute_base_step(times: np.ndarray) -> float:
        diffs = np.diff(np.sort(times))
        diffs = diffs[np.isfinite(diffs) & (diffs > 0)]
        base_step = float(np.median(diffs)) if diffs.size else 1.0
        if not np.isfinite(base_step) or base_step <= 0:
            base_step = 1.0
        return base_step

    def reset(self, dates: np.ndarray | None) -> None:
        self.dates_real = None if dates is None else np.array(dates, copy=True, dtype=float)
        self.time_is_collapsed = False
        self.time_map = None
        self.stream_source_id = None
        self.stream_interval = None

    def append_source_timestamp(
        self,
        timestamp: float,
        *,
        source_id: str,
        interval: float,
        spacing: str,
        use_local_time: bool,
    ) -> tuple | None:
        if self.dates_real is None or self.dates_real.size == 0:
            raise ValueError("Cannot stream an empty collapse source")
        previous = float(self.dates_real[-1])
        if self.stream_source_id not in (None, source_id):
            raise ValueError("Streaming cadence belongs to a different collapse source")
        if self.stream_interval is not None and self.stream_interval != interval:
            raise ValueError("Streaming cadence changed without replacing the source data")
        self.stream_source_id = source_id
        self.stream_interval = interval
        next_map_snapshot = None
        next_dates = np.append(self.dates_real, float(timestamp))
        if self.time_is_collapsed:
            if self.time_map is None:
                raise RuntimeError("Collapsed chart has no time map")
            next_map_snapshot = self.time_map.append_source_in_place(
                previous,
                timestamp,
                interval=interval,
                spacing=spacing,
                use_local_time=use_local_time,
            )
        self.dates_real = next_dates
        return next_map_snapshot

    def find_gaps_and_chunks(self, dates: np.ndarray) -> list[dict]:
        return find_gaps_and_chunks(dates)

    def build_gaps_report(self, dates: np.ndarray) -> tuple[list[dict], str]:
        gaps_n_chunks = self.find_gaps_and_chunks(dates)
        if not gaps_n_chunks:
            return GapReport(gaps_n_chunks, "")

        counts = {}

        def detect_label(obj):
            """Return 'Gap', 'Chunk' or fallback 'Item' based on contents."""
            try:
                # prefer explicit type key
                if isinstance(obj, dict):
                    for k in obj:
                        if str(k).lower() == "type":
                            v = str(obj[k]).lower()
                            if "gap" in v:
                                return "Gap"
                            if "chunk" in v:
                                return "Chunk"
                # search keys/values for hints
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        ks = str(k).lower()
                        vs = str(v).lower()
                        if "gap" in ks or "gap" in vs:
                            return "Gap"
                        if "chunk" in ks or "chunk" in vs:
                            return "Chunk"
                else:
                    s = str(obj).lower()
                    if "gap" in s:
                        return "Gap"
                    if "chunk" in s:
                        return "Chunk"
            except Exception:
                pass
            return "Item"

        lines = []
        for gc in gaps_n_chunks:
            label = detect_label(gc)
            counts[label] = counts.get(label, 0) + 1
            lines.append(f"{label} {counts[label]}:")

            if isinstance(gc, dict):
                # print each key/value on its own line
                for k, v in gc.items():
                    lines.append(f"  {k}: {v}")
            else:
                # try to handle mapping-like objects, otherwise fall back to str()
                try:
                    items = getattr(gc, "items", None)
                    if callable(items):
                        for k, v in items():
                            lines.append(f"  {k}: {v}")
                    else:
                        lines.append(f"  {gc}")
                except Exception:
                    lines.append(f"  {gc}")

            lines.append("")  # blank line between entries

        str_out = "Gaps and Chunks found:\n" + "\n".join(lines)
        return GapReport(gaps_n_chunks, str_out)

    def collapse_dates(
        self,
        dates: np.ndarray,
        *,
        use_local_time: bool,
        debug: bool = True,
        base_step: float | None = None,
    ) -> np.ndarray:
        orig_dates = np.array(dates, copy=True, dtype=float)
        self.dates_real = np.array(orig_dates, copy=True, dtype=float)

        base_step = self._compute_base_step(orig_dates) if base_step is None else float(base_step)

        gaps_n_chunks = self.find_gaps_and_chunks(orig_dates)
        if debug:
            print(gaps_n_chunks)

        total_shift = np.zeros_like(orig_dates, dtype=float)
        ordered = np.sort(orig_dates[np.isfinite(orig_dates)])
        gap_indices = _gap_indices(ordered, base_step)
        for gap_index in gap_indices:
            start = float(ordered[gap_index])
            stop = float(ordered[gap_index + 1])
            remove = float(stop - start - base_step)
            total_shift[orig_dates >= stop] += remove
            if debug:
                print(
                    f"Will collapse gap from {start} to {stop}, remove {remove} seconds "
                    f"(delta={gap_delta}, base={base_step})."
                )

        collapsed_dates = orig_dates - total_shift

        # Build the mapping from original real times (robust to all missing-data gaps).
        try:
            self.time_map = GapCollapsedTimeMap.from_real_series(
                np.array(self.dates_real, copy=False, dtype=float),
                use_local_time=use_local_time,
                base_step=base_step,
            )
            self.time_is_collapsed = True
        except Exception as exc:
            if debug:
                print(f"[GapCollapseManager] Failed to build time map: {exc}")
            self.time_map = None
            self.time_is_collapsed = False

        return collapsed_dates

    def collapse_dates_vectorized(
        self,
        dates: np.ndarray,
        *,
        use_local_time: bool,
        debug: bool = True,
        base_step: float | None = None,
    ) -> np.ndarray:
        """Vectorized gap-collapsing implementation.

        This matches collapse_dates while applying each gap shift with NumPy masks.
        It removes only (gap_delta - base_step), preserving one normal interval
        between the last sample before a gap and the first sample after it.
        """
        orig_dates = np.array(dates, copy=True, dtype=float)
        self.dates_real = np.array(orig_dates, copy=True, dtype=float)

        base_step = self._compute_base_step(orig_dates) if base_step is None else float(base_step)

        gaps_n_chunks = self.find_gaps_and_chunks(orig_dates)
        if debug:
            print(gaps_n_chunks)

        total_shift = np.zeros_like(orig_dates, dtype=float)
        ordered = np.sort(orig_dates[np.isfinite(orig_dates)])
        gap_indices = _gap_indices(ordered, base_step)
        for gap_index in gap_indices:
            start = float(ordered[gap_index])
            stop = float(ordered[gap_index + 1])
            remove = float(stop - start - base_step)
            total_shift[orig_dates >= stop] += remove
            if debug:
                print(
                    f"Will collapse gap from {start} to {stop}, remove {remove} seconds "
                    f"(delta={gap_delta}, base={base_step})."
                )

        collapsed_dates = orig_dates - total_shift

        try:
            self.time_map = GapCollapsedTimeMap.from_real_series(
                np.array(self.dates_real, copy=False, dtype=float),
                use_local_time=use_local_time,
                base_step=base_step,
            )
            self.time_is_collapsed = True
        except Exception as exc:
            if debug:
                print(f"[GapCollapseManager] Failed to build time map: {exc}")
            self.time_map = None
            self.time_is_collapsed = False

        return collapsed_dates
