# Change: Add Econometric Series and Collapse Source Coordination

## Why
DearCyFi can currently load and collapse one candlestick timeline, but it has no provider-neutral scalar time-series type for weekly or monthly econometric data. Adding an econometric line beside higher-frequency candles also requires the chart to distinguish the series that defines removable gaps from follower series that only synchronize with the resulting timeline.

## What Changes
- Add a reusable econometric line series backed by DearCyGui native line and scatter elements, with basic observation tooltips.
- Preserve separate source timestamps and plotted timestamps so tooltips retain real dates after gap collapsing.
- Add a chart-level time-series registry and `collapse_source_id` selection mechanism.
- Build the gap map only from the selected collapse source and project registered follower series through that map.
- Define initial `next` and `previous` projection policies for follower timestamps that fall inside a removed primary-series gap.
- Preserve existing candle-only behavior by registering candles as the default collapse source when no source has been selected.
- Add a demo-owned toy econometric provider widget, normalized request/result types, and deterministic weekly fake data for exercising the new series beside collapsible hourly candles.
- Add automated tests for econometric data validation, collapse-source ownership, follower projection, source-date preservation, and deterministic toy data.

## Impact
- Affected specs: `econometric-series` (new), `time-collapse-coordination` (new), `demo-data-source-widgets` (new)
- Affected code:
  - `src/dearcyfi/core.py`
  - `src/dearcyfi/candle_utils/gap_utils.py`
  - New econometric plotting module under `src/dearcyfi/`
  - `src/dearcyfi/__init__.py`
  - New provider widget modules under `examples/DearCyFi_Demo/data_widgets/`
  - `examples/DearCyFi_Demo/DearCyFi_Demo.py`
  - Tests under `tests/`
- Compatibility: existing `DearCyFi.set_data(...)` and candle-only collapse calls remain supported. No provider SDK or new runtime database dependency is introduced.
