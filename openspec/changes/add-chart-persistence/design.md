# Design: Portable chart snapshots

## Context

`DearCyFi` owns candles and horizontal bars, the time-series registry and collapse map, the candle indicator manager, and a registry of interactive tools. Registered `PlotEconometricSeries` instances already retain source timestamps separately from their projected dates. A range box has source geometry distinct from rendered geometry. The demo owns providers, stream tasks, and per-series legend widgets. A snapshot should use these ownership boundaries rather than walk the DearCyGui widget tree.

The existing plot context menu is the shared UI entry point. The custom DearCyGui plot-item API distinguishes `enabled` (the native legend toggle) from `show` (which also removes the legend entry); restoring one is not a substitute for restoring the other.

## Decisions

### A self-contained, versioned data model

Use plain Python dictionaries, lists, and JSON primitives with a separate codec. The root has a fixed format marker (`"dearcyfi-chart"`), integer `version: 1`, `chart`, and ordered `series`, `indicators`, and `drawings` arrays. An empty chart is valid. Representative record layout:

| Section | Version 1 shape |
|---|---|
| `chart` | `axes` keyed by `X1`, `Y1`, `Y2`, `Y3`; `time` for source selection, gap state and date presentation; chart-level legend and anchor-tooltip settings |
| `series[]` | `id`, `kind`, `data`, `display`; `in_gap` for registered source-time series |
| `indicators[]` | `id`, `kind`, `input`, `parameters`, `display`; SMA uses `input: "candles"`, `period`, and `field` |
| `drawings[]` | `id`, `kind`, `geometry`, `options`, `display`; `range-box` uses `left_time`, `right_time`, `bottom`, `top` |

Use stable kind tokens such as `candles`, `econometric`, `horizontal-bars`, `sma`, and `range-box`, not Python class names or DearCyGui UUIDs. Keep instance IDs and the IDs used for time-series registration stable; the existing indicator registration ID can be derived from its instance ID. Keep the per-collection order of saved records. Reject duplicate IDs in their ownership namespaces, including collisions in the effective time-series registry. Future creates must not collide with restored IDs.

- Candles use column arrays of source timestamps and OHLC values, with volume and an explicit index when present. Distinguish the default index from a supplied JSON-scalar index; do not convert opaque index objects to strings. Candle and volume display are distinct where the renderer already treats them as distinct.
- Econometric series store source timestamp and value columns at their own cadence, with their gap-following policy. Do not infer cadence from candles, fill gaps, drop observations, or store the projected X array. Horizontal bars use their actual lengths and price levels and data/normalized presentation, not a random seed or source-time projection.
- Indicator definitions are authoritative. Reuse the indicator registry and manager to validate and compute outputs from the restored candles, including SMA warm-up. An SMA defined on an empty chart may remain empty until candles are loaded. Do not write calculated values or make EMA/RSI depend on SMA's parameter names.
- Restore range-box coordinates, axis, colors, hit size, minimum size, and tooltip options using the existing tool lifecycle. Geometry is canonical source time and Y values; never save drag-start copies, hit regions, or hover state. Future drawings can define their own semantic anchors and typed geometry.
- Use explicit allowlists per kind for presentation: labels, symbolic Y axes, RGBA colors, relevant line/marker/candle/bar styles, tooltip switches, and plot item `show`, `enabled`, `no_legend`, and `ignore_fit` where supported. Do not dump `**kwargs`, runtime state, custom formatters, themes, or fonts. Restore standard formatters; host callbacks and custom decorations can be attached again by the host. Other unregistered host-owned plot children are outside the format and are not deleted by Open.

Use Unix seconds in UTC for source timestamps and drawing anchor times. Display date mode (local/UTC, 12/24 hour, ISO, date-context labels) is separate; local mode uses the destination machine's timezone. Use finite JSON numbers for coordinates and options. In supported sample-value columns that can contain missing observations, encode a missing value as `null` and decode it to the built-in type's missing representation; an econometric `null` restores a line break. Infinity is not missing. Validate values and timestamp ordering using each built-in's data contract; do not silently sort, deduplicate, or coerce input. Reject JSON `NaN`/`Infinity`, duplicate object keys, and nonrepresentable numeric values.

### Restore collapse before restoring the view

Persist the collapse source selection even when the chart is in original time, and persist the preferred method for the next collapse separately from the active map. If collapsed, store the active map as compact source gap boundaries and the retained width of each gap, with the origin implied by the earliest source sample. An empty gap list is valid for an active map with no removed intervals. Validate ordered, non-overlapping gaps against adjacent source timestamps, with each retained width positive and shorter than its source interval. Rebuild projections, map indexes, and calendar caches with the existing gap logic. Do not store per-item projections or serialize internal map objects. Re-inferring the gaps from the final source timestamps alone can change a map that was extended incrementally.

Store initialized, finite axis limits, visibility/enabled state, labels, and supported scale modes. Axis limits are in each axis's coordinate space: the `X1` range is explicitly tagged `source` or `collapsed` to match the saved time state. Unlike data and drawing coordinates, the X1 view limits stay in the rendered frame: an edge can be inside a retained gap where translating it through source time can be lossy. Apply ranges after projection and initial layout so fit and axis callbacks do not overwrite the saved zoom. When a range was not initialized, use normal initial fit/default behavior for that axis only. Do not save plot pixel dimensions, ticks, diagnostics, or transient GUI state.

### Explicit extension and validation

Keep the document version separate from the record kind. Add kind handlers explicitly in code, reusing existing factories where appropriate. Each owns validation, capture and rehydration of its type-specific data; adding a supported kind does not by itself require a new root schema. No module paths, executable fields, dynamic imports, pickle, or network access on load. Reject an unknown kind or unsupported document version with an actionable diagnostic rather than opening a partial chart. If a later revision changes the schema incompatibly, add an explicit migration or report that the reader cannot open it; there is no legacy reader to migrate in this change.

Validate the file as untrusted data before publishing anything: format/version, schema fields and array shapes, numeric values and bounds, cross-references, axis and option enums, and kind-specific data/geometry rules. Reject unrecognized fields rather than discard their meaning. If a participating chart-owned series, indicator, or drawing has no supported snapshot representation, fail Save with the item and reason rather than silently omit it. Host-specific runtime hooks are outside the file contract, not data extensions. Enforce a 64 MiB UTF-8 document limit on read and write, including bounded reads when the file changes between size check and read. Prefer column arrays and one validation pass; no background thread mutates a DearCyGui object.

### Transaction and file boundaries

Expose a detached dictionary capture and validate-and-restore API plus file helpers (proposed: `capture_chart_state`, `restore_chart_state`, `save_chart`, `open_chart`). File helpers and menu actions share the same validation and transaction path; explicit programmatic restore needs no UI confirmation, and programmatic Save defaults to no overwrite.

- **Save:** capture one coherent revision on the chart's mutation boundary, including the current data of a forming candle. Encode/write away from the render callback; write a temporary file beside the destination and atomically publish it only on success. Never clobber an existing destination without permission; handle a target appearing after the check. Report path or write errors, and clean up temporary files.
- **Open:** read and prepare the document, then publish to the same chart on its existing mutation boundary. Build and validate replacements for source series, derived indicators, and tools; restore source selection, projections, presentation, and view in that order. Keep the previous state available until commit; a construction, projection, or publication error must leave the prior chart and managed UI usable. Dispose old managed items, their tooltips, and stale legend controls only after successful replacement. Notify hosts after commitment so they can rebind their own references and UI.
- **Demo:** allow Save during streaming as a point-in-time snapshot. Serialize Open publication with the stream and provider reload path. A successful Open stops or invalidates old producers before they can write to the restored chart; cancellation and rejected loads do not stop the original feed. Do not reconnect automatically. Rebind the demo's indicator menus and econometric reference to the restored instances; drop stale popups and references. The comparison plot and provider selection controls are not restored.

### Context-menu workflow

Add **Save Chart...** and **Open Chart...** without replacing the native menu or the current collapse/diagnostic entries. Use a DearCyGui popup with a path field, action and Cancel buttons, and clear status/error text; no OS-specific picker is required. UI Save appends `.json` when the path has no suffix. Show the resolved target on overwrite confirmation, and confirm replacement of the current chart before publishing Open. Errors leave the popup usable for correction or retry. Parse and write outside the render callback; serialize commits on the chart boundary and prevent overlapping submissions. Until commit begins, Cancel prevents publication, and a late completion must not update a dismissed popup. The library owns this workflow; the demo only supplies integration for its runtime state.

## Trade-offs

- Embedded JSON is readable, portable, and offline, but larger than binary or provider references. Version 1 is a bounded snapshot, not storage for unlimited historical feeds.
- Reconstructing instances preserves logical IDs, not Python/GUI object identities. A host holding a reference to a replaced series must reacquire it after Open. Arbitrary host-owned overlays remain the host's responsibility.
- Treat opening as replacement, not merge. A successful Open replaces supported chart contents absent from the document as well as those present; an empty valid snapshot clears them. There is no undo, automatic backup, or app-wide workspace persistence in this change.
