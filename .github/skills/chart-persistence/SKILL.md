---
name: chart-persistence
description: Use when adding or modifying chart snapshot kinds, validation, versioning, capture, or transactional restore for DearCyFi.
---

# DearCyFi Chart Persistence

The document codec is in `src/dearcyfi/_chart_document.py`; the GUI adapters
and restore transaction are in `src/dearcyfi/_chart_state.py`. Keep JSON data
independent of DearCyGui objects, hosts, and providers.

## Adding a Kind

1. Pick a stable kind token and use the owning manager's stable instance ID,
   not a display label, GUI UUID, or class name. Check duplicate IDs in the
   owning collection and any derived time-series registration namespace.
2. Define only the kind's input dependencies and parameters, source sample
   columns, or canonical source-time geometry. Never store calculated results,
   projected dates, render primitives, hover state, callbacks, or arbitrary
   constructor kwargs. Use explicit options and display fields. Do not store
   series `show` or `enabled`: reopened series start visible.
3. Add a validator to the appropriate codec allowlist, and explicit capture
   and restore handlers to the matching state adapter tables. Reject bad
   shapes, values, fields, and references before publication. Include the
   record's ID or field path in errors.
4. Construct via the existing manager or factory in the detached staging
   chart. Register the same ID and dependencies; defer projection and view
   publication to the existing transaction. Keep host-owned items out of it.
5. Test round trips (including subsequent edits), source vs. collapsed
   coordinates, and invalid records that leave the original chart unchanged.
   Include tests for effective registration collisions and empty inputs when
   the kind supports them.

## Examples

- `sma`: `_capture_sma` stores the candle dependency, period, field, and
  supported line options. `_restore_sma` calls `CandleIndicatorManager.create`
  with the saved ID and computes the output from restored candles, including
  warm-up gaps. Future indicators define their own parameters.
- `range-box`: `_capture_range_box` reads `source_geometry`, the Y axis, and
  interaction and color options. `_restore_range_box` constructs the
  `RangeBoxTool` and registers it through the chart's tool lifecycle. Collapse
  reapplies projection after staging; draw objects and drag state are never
  loaded.

Adding a kind with the existing envelope does not by itself require a schema
version change. Older readers reject unknown kinds without partially opening the
chart. Incompatible required-field or interpretation changes need a new
version and, when supported, an explicit validating migration. Never use
dynamic imports or executable fields to open an unknown kind.
