# Change: Render Econometric Series as One Drawing Item

## Why

The econometric line, observation markers, and tooltip hit regions are separate plot items. Hiding the line through its legend leaves the markers and interaction regions active.

## What Changes

- Replace the native line and scatter plot items with line and marker primitives inside one legend-enabled `DrawInPlot` item, following the candle drawing pattern.
- Put observation hit regions in the same item so hiding the series also disables its interactions.
- Preserve missing-value breaks, source and plotted timestamps, axis selection, fitting, complete updates, and collapse coordination. Markers remain optional and retain a consistent screen-space size when zooming.
- **BREAKING:** The existing `line` and `markers` attributes will no longer be native `PlotLine` and `PlotScatter` objects. Replace native-specific `line_kwargs` and `marker_kwargs` with a documented, explicit primitive styling API; reject unsupported legacy options rather than silently ignoring them.
- Leave candle and volume rendering unchanged.

## Impact

- Affected spec: `econometric-series`.
- Affected code: `src/dearcyfi/econometric_series.py`.
- Affected tests and documentation: econometric rendering and collapse tests, demo validation, and `README.md`.
- Dependencies: `add-econometric-series-collapse-source` and `add-series-y-axis-assignment` are completed but unarchived. Archive the former before archiving this change so its modified requirements exist in the baseline. Preserve the latter's axis requirements; its conflicting-`axes` extension-kwargs scenario remains satisfied because legacy kwargs, including any containing `axes`, are rejected with a clear error.
