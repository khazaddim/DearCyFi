# Change: Add portable chart snapshots

## Why

DearCyFi can assemble candles, econometric observations, moving averages, and interactive drawings on one chart, but users cannot reopen that work. A self-contained JSON snapshot lets them resume or share a chart without needing the original data source or a database.

## What Changes

- Add a versioned, provider-independent JSON format and programmatic capture, restore, save, and open for one `DearCyFi` chart.
- Embed the chart's current candle data and volume, registered econometric observations, and any chart-owned horizontal bars. Store SMA definitions and range-box geometry by type and stable ID; recompute indicator output and rebuild interactive objects on open.
- Restore the saved axes and zoom, series and legend visibility, and original or collapsed time state. Preserve the active gap layout even when it was extended by streaming.
- Add **Save Chart...** and **Open Chart...** to DearCyFi's existing right-click plot menu. Use a chart-owned popup and explicit confirmation before overwriting a file or replacing the current chart's contents. Cancel or failure must not partially replace either.
- Define how future EMA, RSI, Fibonacci retracements, price channels, and other supported types can add persistence without changing the common document structure. Do not implement those tools or calculations in this change.

## Scope and Impact

- New capability: `chart-persistence`. The existing indicator, drawing, axis, series, and collapse contracts continue to apply; this change adds a way to restore their state.
- Expected changes: DearCyFi core and a JSON codec, built-in series and tool adapters, plot context menu, demo lifecycle integration, tests, and documentation. No database, provider SDK, or new mandatory GUI dependency.
- One chart per file. No whole-workspace layout, autosave, live-feed restoration, or serialization of arbitrary DearCyGui objects or host callbacks. The demo's separate comparison plot is not part of a snapshot.
- Existing chart construction and mutation APIs keep their behavior. A DearCyGui path-entry popup is sufficient for the first release; no OS-specific file picker is required.
- Snapshot files contain the actual plotted source data, which may be private or licensed. They are local files, not encrypted containers or uploads.

## Approval

Proposal only. Review and approve before implementation.
