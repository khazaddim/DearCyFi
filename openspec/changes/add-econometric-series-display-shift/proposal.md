# Change: Add Econometric Series Display Shifts

## Why

An econometric signal may lead market data and extend beyond the latest candle. A future trading calendar is not currently available, so exact future gap collapse is not possible. An approximate shift applied after projection can support exploratory comparisons without changing the historical candle-derived gap map.

## What Changes

- Allow an econometric follower to shift forward or backward on the displayed time axis, with separate collapsed and uncollapsed shift settings.
- Accept shifts expressed as collapsed candle intervals or approximate calendar weeks; derive an initial uncollapsed setting from average historical compression and allow independent adjustment.
- Keep original observation timestamps and values intact, and preserve shifts across collapse/restore and streaming updates.
- Show approximate horizontal uncertainty ranges for shifted points beyond the candle endpoint, estimated from the historical distribution of compressed time.
- Prevent future axis and cursor presentation from implying that unknown future market dates are exact.
- Document the approximation and provide deterministic tests and a demo validation path.

## Scope And Non-Goals

- Candles remain the authoritative source for observed historical gaps; no synthetic candles or future market calendar are introduced.
- Uncertainty ranges describe an estimate of timing variation associated with historical compression, not the predictive accuracy of the signal or a statistical confidence interval.
- Correlation calculations, automatic lag selection, and provider-specific liquidity loading are outside this change.
- The exact uncertainty estimator and its conversion to displayed coordinates require design review before implementation; see `design.md`.

## Impact

- Affected capability: `econometric-series-display-shift` (new).
- Related unarchived changes: `add-econometric-series-collapse-source`, `refactor-econometric-series-drawing`, `add-incremental-series-streaming`, and `add-collapsed-time-cursor-tag`.
- Expected code areas: econometric rendering and tooltips, chart-managed projection and streaming, future axis/cursor presentation, tests, demo controls, and documentation.
- Compatibility: zero shift preserves current behavior; existing consumers do not need to configure a shift.

## Approval

This is a proposal only. Resolve the estimator and other open design questions, then obtain approval before implementation.
