## Context

`DearCyFi.set_data(...)` replaces candle arrays, restores a collapsed chart, registers the candle adapter, and resets the gap manager. Registered series already distinguish source dates from plot dates and support shared projection. Candles and scalar econometric series currently redraw from full arrays.

`GapCollapsedTimeMap` records piecewise time segments and date-boundary anchors. Its current projection extrapolates beyond the last source timestamp using the final cumulative shift. A newly appended source timestamp can reveal that some previously extrapolated follower timestamps actually lie inside a new removed gap.

The existing full gap builders infer spacing using median differences, with integer conversions in some helpers. The streaming path must retain a single finite positive interval in seconds and use consistent precision for validation and tail mapping; it must not repeatedly invoke those full builders.

## Goals / Non-Goals

Goals:
- Separate append, latest-value modification, and latest-interval lookup.
- Support provider-neutral mutable time-series registrations and candle convenience calls.
- Keep streaming cadence stable and maintain collapsed timelines incrementally.
- Preserve real timestamps, follower semantics, annotations, and presentation.

Non-goals are listed in the proposal. In particular, this change does not implement a broker connector or the initial historical collection loop.

## Decisions

### Public operations and ownership

Expose synchronous chart methods:

```python
check_last_sample(series_id, timestamp) -> tuple[bool, float | None]
append_sample(series_id, *, timestamp, **values) -> None
update_last_sample(series_id, **values) -> None

check_last_candle(timestamp) -> tuple[bool, float | None]
append_candle(*, timestamp, open, high, low, close, volume=0.0) -> None
update_last_candle(*, open=None, high=None, low=None, close=None, volume=None) -> None
```

The candle methods delegate to the `"candles"` registration. Generic operations use the registered series' schema: `open/high/low/close/volume` for candles and `value` for scalar econometric observations. Candle `None` defaults mean unchanged; generic payloads use omitted fields for unchanged values and do not silently accept `None` as numeric data.

Retain the existing source-date/projection registration contract. Add a minimal optional mutation adapter capability for validation, preparing append/latest-update state, and committing it. Implement it for candles and scalar econometric series; keep payload validation series-specific rather than adding a broad universal data model. Unsupported mutation attempts fail clearly, while projection-only registrations still collapse and restore normally.

The chart owns mutation coordination so direct data changes cannot bypass its source/follower map lifecycle. Keep chart candle arrays, indexes, per-candle annotations, series arrays, volume, and tooltip data consistent. Append an empty annotation entry when existing annotations require one; extend default indexes sequentially and custom indexes with an explicitly documented timestamp-derived label, without inventing a numeric successor for arbitrary labels.

### Stable cadence from loaded history

Streaming mutation requires at least two finite strictly increasing source timestamps and a finite positive median of their adjacent differences. Compute this interval once, lazily if appropriate, from the existing loaded history in floating-point seconds, without integer truncation. Do not infer cadence from another series or from the incoming event.

Each mutable series has its own cadence. Only the selected collapse source controls the shared map. Reject streaming mutation if cadence cannot be established; do not assume one second or bootstrap an empty series. Full data replacement invalidates the cached cadence and retains its existing restore/reset behavior.

Appending does not recalculate the median. Otherwise a changing median could retroactively change historical gap classifications. For example, a daily series retains a one-day interval through an irregular two-day arrival.

### Timestamp occupancy and numerical tolerance

All timestamps are finite real Unix seconds. Adapters convert provider units and normalize timestamp meaning before calling the API. A candle timestamp identifies its interval start; the check method also accepts event times inside that interval.

For latest start `s` and cached interval `h`, match the half-open interval `[s, s + h)`. Before comparison, snap timestamps within tolerance of either boundary to that boundary; the lower boundary matches and the upper boundary belongs to the next interval.

Use the same tolerance helper for lookup and append validation. Proposed deterministic tolerance in seconds:

```text
tau = max(min(0.001, h * 1e-6), 8 * max(ulp(s), ulp(t), ulp(s + h)))
```

Here `t` is the candidate timestamp and `ulp` is floating-point representational spacing. Reject a timestamp/interval combination if this tolerance is at least half the interval; precision must not make adjacent intervals indistinguishable. This is a numerical boundary tolerance, not permission to accept materially shorter candle intervals.

Lookup is read-only and returns `(matches, stored_latest_timestamp)`, even on a miss. An existing empty series returns `(False, None)`; a non-empty series without an inferable cadence raises a clear error. Unknown series IDs and invalid timestamps raise errors.

Example: with five-minute spacing and latest start 10:00, 10:03 matches, while 10:05 does not. This does not authorize appending a new candle at 10:03.

### Append and latest-update semantics

`append_sample` never implicitly modifies the latest sample. Let `delta = t - s`. For a valid timestamp and payload, these are the three exhaustive spacing cases, with equality interpreted using the shared numerical tolerance:

| Spacing from the latest start | Collapsed chart, selected source append | Uncollapsed chart |
| --- | --- | --- |
| Less than the cached median interval (`delta < h - tau`) | Reject without mutation | Reject without mutation |
| Equal to the cached median interval within tolerance | Append using the existing cumulative shift; remove no additional time | Append at the real source timestamp |
| Greater than the cached median interval (`delta > h + tau`) | Record the new gap and append after removing only the excess `delta - h` | Append at the real source timestamp; do not collapse |

A duplicate or earlier timestamp belongs to the rejected case. A longer interval need not be an integer multiple of `h`. Preserve the accepted source timestamp rather than replacing it with a rounded or collapsed timestamp. For a normal continuation within tolerance, preserve its actual elapsed spacing. For a longer interval on a collapsed source, the new plotted coordinate is the previous source endpoint's plotted coordinate plus `h`; historical source plot coordinates do not move.

An uncollapsed append performs no coordinate collapse, follower reprojection, or tool projection refresh caused by gap removal. Recording tail metadata for a later explicit collapse does not change displayed coordinates. A collapsed follower append uses the selected source's existing map, not independent gap removal; see below.

`update_last_sample` changes only supplied latest values and never changes timestamps, count, cadence, or map geometry. Reject an empty update. Candle values are replacements, including volume, not additions or inferred running extrema. Validate the complete resulting candle (`low <= open/close <= high`, finite OHLC, finite nonnegative volume) before committing; callers can update multiple fields together when needed. Scalar series retain their existing missing-value rules.

Both operations require established cadence and preserve all earlier observations. Older event correction is outside this API; a lookup miss is not proof that append will be valid.

### Incremental gap state and dependent projections

For an appended collapse-source observation while collapsed, extend the last retained segment on normal spacing. On a gap, retain the previous segment endpoint, append a gap record and a new retained segment, and add `delta - h` to the cumulative removed duration before plotting the appended observation. Update segment lookup indexes and only newly crossed day/month/year anchors using the existing timezone policy.

Do not scan historical timestamps, recompute their median, rediscover historical gaps, or alter existing source coordinates. Keep equivalent incremental gap metadata available while uncollapsed so collapse after streaming uses the accepted cadence and gap history. The first map initialization may scan loaded history once; steady-state append may not.

In collapsed mode, when a new gap is removed, reproject registered follower observations whose source timestamps are after the previous source endpoint, including points inside the newly discovered gap and points beyond the new endpoint. Reuse earlier plot coordinates. Honor each follower's existing `next`/`previous` policy. A normal continuation changes no existing projections; a latest-value update changes none either. In uncollapsed mode, followers and tools stay at their real source coordinates.

A follower append projects only its new timestamp through the active map and never extends that map. This also applies to candle appends when another registration is the selected source. No follower is filled, resampled, or treated as a gap-detection input.

Refresh registered drawing tools after a source map extension from canonical source-time geometry. A refresh of all tools is acceptable; historical gap rebuilding is not. Keep axis date anchors, cursor expansion, volume positions, chart date caches, and subsequent collapse/restore behavior consistent.

Gap detection and map-tail extension should require constant work relative to history, excluding date anchors actually added. Follower coordinate work is proportional to the affected observations, not the complete historical dataset. Existing renderers may redraw a changed series; this proposal makes no constant-time rendering promise.

### Validation and publication

Prepare incoming values, resulting arrays, candidate map-tail changes, and follower projections before publishing. Any rejected input or preparation failure leaves data, cadence, map, and presentation untouched. If applying a prepared series or tool update fails, restore the previous coherent state and surface the error; do not silently restore to uncollapsed time or report success.

Preserve series identity, selected source, collapse state, legend visibility, styles, Y-axis assignment, tool source anchors, and user viewport limits. Do not fit or follow the latest candle automatically. Wake the viewport after successful mutation using the existing DearCyGui mechanism.

### Asynchronous providers remain outside the core

Provider tasks normalize events and marshal them onto the host's serialized chart-update boundary. Check and subsequent mutation must execute together there, with no `await` between them; the read-only check is not an atomic upsert or a concurrency lock.

Document this provider-neutral consumer pseudocode:

```python
def apply_event(chart, event):
    exists, latest_timestamp = chart.check_last_candle(event.timestamp)
    if exists:
        chart.update_last_candle(**event.ohlcv)
    else:
        chart.append_candle(timestamp=event.timestamp, **event.ohlcv)
```

The host awaits its provider outside this callback, enqueues the callback, and reports validation errors explicitly. Provider candle messages should use candle-start timestamps; hosts feeding intra-interval ticks must handle aggregation themselves. Initial bulk collection and its timeout remain future adapter work.

### Synthetic demo stream

Extend the demo's existing fake candle controls rather than adding a real-provider widget. The host owns the stream lifecycle and chart mutations; the controls request start, stop, and a gap in the next appended candle. Use a deterministic seed and a configurable update period so a user can observe several valid OHLCV revisions of the current candle followed by a new candle without waiting for the displayed candle interval. Timestamps remain interval starts in Unix seconds, with the interval derived from the loaded series' streaming cadence.

Start from the already bulk-loaded synthetic candles, require enough history to establish cadence, and apply events through the chart's public candle operations at a serialized host update boundary. Keep the original-time comparison plot synchronized with the same observations at real timestamps. The existing econometric follower remains available to observe shared collapse behavior; no synthetic econometric stream is required.

Stop and await or otherwise finish the producer before reloading candles, changing the selected toy symbol, or shutting down. Starting twice must not create concurrent streams; restarting uses the currently loaded data, not stale generator state. Display running, stopped, and error status, and stop on a mutation failure rather than silently dropping an event. Do not automatically fit or follow the stream. The synthetic stream is a visual and functional demonstration, not a throughput or large-series benchmark.

## Risks / Trade-offs

- The historical median may not represent a calendar-based or mixed-frequency feed. This API deliberately enforces the loaded elapsed-time cadence; shorter DST/calendar arrivals can fail and require a separate cadence-policy proposal.
- Precision tolerance must be tested at realistic epoch magnitudes, not only near zero.
- Followers may contain future-shifted points, so updating only the newest follower point would be incorrect when the source discovers a gap.
- Transactional publication and restoring failed render updates need focused failure-injection tests.
- Renderer rebuilding can remain the dominant cost even with incremental map maintenance.

## Migration

This is additive. Existing consumers can continue replacing whole datasets. Consumers opting into streaming bulk-load first, then use the serialized check/update-or-append workflow. No SDK or new runtime dependency is required.
