# Change: Move gap controls into the chart context menu

## Why

DearCyFi's time-collapse controls are separate from the chart. The custom
DearCyGui build now supports extending the native plot context menu.

## What Changes

- Add chart-owned `Collapse Time` and `Vectorized Collapse` checkboxes and a
  `Gaps n' Chunks` action to the native plot context menu.
- Default to vectorized collapse; changing the method affects the next
  collapse, not an already-collapsed chart.
- Move the date-context labels and both diagnostics toggles into a chart-owned
  `Diagnostics` submenu. Show the selected collapse source in the menu.
- Keep checkmarks synchronized with actual chart state and properties, including
  direct API calls, data replacement, source changes, and failed collapse.
- Move the bar-loading button and bar-length mode selector to `Fake Candle
  Controls`, then remove the empty `Collapsing Controls` section.
- Preserve all existing programmatic APIs.
- Preserve the native plot menu, add focused tests, and update documentation.

## Impact

- Affected spec: `time-collapse-coordination`.
- Affected code: DearCyFi core, demo submodule, focused tests, documentation.
- Requires the new custom DearCyGui build with plot context-menu support;
  unsupported builds must produce a clear compatibility error. No DearCyGui
  changes or replacement of its native menu are included.
