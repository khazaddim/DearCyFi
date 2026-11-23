# Change: Add provider-neutral incremental series streaming

## Why
Streaming providers deliver both new observations and revisions to the latest observation. DearCyFi currently exposes full-dataset replacement, which restores collapsed charts and rebuilds series rather than offering an explicit append/latest-update workflow.

Consumers need to distinguish a forming candle from a new candle using real timestamps, reject arrivals closer than the established cadence, and incrementally record new gaps without rescanning historical data. Registered followers, including the demo liquidity series, must remain synchronized with the shared timeline.

## What Changes
- Add separate chart-managed operations to check the latest observation's time interval, append one observation, and partially modify the latest observation.
- Expose candle convenience methods: `check_last_candle(timestamp)`, `append_candle(...)`, and `update_last_candle(...)`.
- Apply the same provider-neutral operations to mutable registered time series, initially candles and scalar econometric series; retain compatibility with projection-only registrations.
- Infer each mutable series' regular interval once from the median positive timestamp spacing of its loaded data, and retain it until full data replacement.
- Match latest observations by interval occupancy with bounded timestamp tolerance, returning both a boolean and the stored latest source timestamp.
- Reject distinct appended observations less than one regular interval after the latest observation; accept arbitrary longer intervals as gaps without requiring integer multiples of the regular interval.
- Make the three spacing cases explicit: reject below median, append without additional gap removal at median, and remove excess spacing above median only when the chart is collapsed; uncollapsed appends retain real timestamps.
- Extend the selected source's gap map at its tail, preserving historical gap records and coordinates, and synchronize affected follower projections, tools, and time-axis presentation.
- Preserve collapsed/uncollapsed state and existing series presentation during updates.
- Document a provider-neutral serialized check/update-or-append loop suitable for use behind an asynchronous provider adapter.
- Extend the demo's synthetic candle controls with a start/stop stream that revises the latest candle, appends new candles, and can introduce a gap for visual testing.

## Scope And Non-Goals
- No broker SDK dependency, authentication, subscription management, or Tastytrade-specific payloads in the core package.
- No initial historical stream collection, timeout policy, or new bulk-loading API; consumers begin with existing bulk-loaded data.
- No arbitrary historical insertion, timestamp correction, automatic upsert, resampling, automatic OHLC aggregation from ticks, or automatic series creation.
- No automatic scrolling, axis fitting, background task framework, or guaranteed constant-time drawing update.
- No real-provider integration, data-lake merging, persistent cache, or large-history benchmark; the demo stream uses synthetic data only.

## Impact
- Affected capabilities: new `incremental-series-streaming`; additive extension to `time-collapse-coordination` introduced by `add-econometric-series-collapse-source`.
- Affected code: `src/dearcyfi/core.py`, `src/dearcyfi/candle_utils/gap_utils.py`, `src/dearcyfi/DCG_Candle_Utils.py`, `src/dearcyfi/econometric_series.py`, demo candle controls and host, related tests, `README.md`, and the demo README.
- Related work: build on the completed `add-econometric-series-collapse-source` change; coordinate econometric renderer edits with the active `refactor-econometric-series-drawing` change without changing its rendering contract.
- Existing `set_data(...)`, full-series replacement, registration, and collapse/restore APIs remain available with their current lifecycle behavior.

## Approval
This is a proposal only. Implementation starts after review and approval.
