## Context

The custom DearCyGui build supports plot-owned widgets inside the native ImPlot
context menu. DearCyFi already owns collapse operations, the selected source,
gap reporting, and diagnostic properties; the demo currently owns the controls.
The demo is a separate Git submodule and its existing worktree and staged
superproject pointer must be preserved.

## Intended menu

Append these chart-owned entries to the existing native plot menu:

```text
Collapse Time                 [checkable]
Vectorized Collapse           [checkable, initially checked]
Gaps n' Chunks
Collapse source: <id or not selected>  [read-only]
Diagnostics >
    Date Context Labels       [checkable]
    Date Context Diagnostic   [checkable]
    Label Overlap Diagnostic  [checkable]
```

Native axis, legend, and settings entries remain unchanged. The existing
`no_menus` and `menu_button` configuration remains authoritative.

## Behavior

- Enabling `Collapse Time` calls `collapse_time_chart_vec` if `Vectorized
  Collapse` is checked, otherwise `collapse_time_chart`. Disabling it calls
  `restore_time_chart`.
- The vectorized checkbox controls the next collapse only; toggling it while
  collapsed does not restore or reproject the active chart.
- The collapse checkbox follows the actual gap-manager state, not just the
  user's requested value. In particular, failure or no source must not leave a
  success-shaped checkmark.
- `Gaps n' Chunks` reuses `add_gaps_chunks_GUI`; output continues to use its
  existing status callback and console behavior.
- Diagnostic checkboxes delegate to `apply_date_context_labels`,
  `date_context_debug`, and `label_overlap_debug`, preserving constructor
  defaults, demo overrides, and axis/overlay behavior.
- The source display follows `collapse_source_id`, including selection, removal,
  and replacement. Existing source selection APIs remain unchanged.

## State and compatibility

Use the chart's actual collapse state and diagnostic properties as the source
of truth. Synchronize menu values after changes from direct API calls and chart
lifecycle operations, and when menu actions fail. Avoid recursive callbacks
when updating values programmatically. Verify the actual installed DearCyGui
widget and callback behavior before selecting a concrete synchronization
mechanism; do not rely on asynchronous callbacks running during menu drawing.

The new custom DearCyGui plot context-menu support is required. An incompatible
build must fail explicitly with an actionable message, not silently omit the
controls. Keep existing Python collapse, restore, source-selection, and
diagnostic APIs available to hosts.

Move the `Load Bar Data` button and `Bar Length Mode` selector from the demo's
`Collapsing Controls` section to `Fake Candle Controls`, preserving their
existing callback and selected-mode behavior. Remove the now-empty
`Collapsing Controls` section. The demo status area remains available for gap
reports.

## Validation

Test scalar and vectorized routing, restore, checkmark synchronization after
direct calls and source/data changes, missing source and failure behavior,
diagnostic properties, source display, unsupported builds, and bar loading in
its new demo location. Verify rendered
interaction with the installed custom wheel, including existing native menu
entries and `no_menus`/`menu_button` behavior. Use existing demo documentation
and targeted test conventions; do not modify DearCyGui itself.

## Open questions

None currently. The selected method applies on the next collapse, and all three
date-context/diagnostic checkboxes belong in `Diagnostics`.
