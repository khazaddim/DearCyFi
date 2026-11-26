## Context

Candles are held by `DearCyFi`; registered time series participate in
projection through a shared time map. Existing registration alone does not
subscribe a derived series to candle values or append its corresponding sample.
The streaming change coordinates publication and rollback for source and
followers, and its demo verification and review remain in progress.

The demo has already demonstrated DearCyGui legend popups by attaching UI
children to each plot item. Candle and econometric redraws preserve those UI
children while replacing drawing children. This proposal builds on that
behavior without modifying DearCyGui.

## Goals / Non-Goals

Goals: reusable calculation and lifecycle contracts; multiple independently
configured SMA instances; synchronization with every supported candle update;
editing and removal through the demo; one legend entry per indicator.

Non-goals: EMA and band formulas, a finished multi-line renderer, arbitrary
provider or historical-correction support, persistent configurations, and
modifying the original-time comparison plot.

## Decisions

### Separate calculation, rendering, and lifecycle

- An `Indicator` calculation contract accepts a candle snapshot and validated
  parameters, and returns named output arrays aligned one-for-one with source
  candle timestamps. SMA initially has one named output. The interface must
  allow future calculations using multiple OHLC fields and multiple outputs;
  this change need not render multiple outputs.
- Implement an SMA calculator as the first concrete indicator. A single
  legend-enabled chart-facing `DrawInPlot` item represents each indicator
  instance; its drawings and hit targets are children of that item.
- An indicator manager owns unique stable instance/registration IDs and
  coordinates create, edit, remove, candle synchronization, and cleanup.
  Callers can also instantiate the SMA calculation directly without the demo.
  A small type registry or factory at the application/manager boundary maps
  the GUI selection to indicator construction and parameter metadata; it must
  not introduce a plugin framework for this single supported type.
- Keep source and plot timestamps separate and use the registered follower
  projection contract. Indicator values align to the candle at the same index
  and use the same plotted X coordinate as that candle, including when a
  different registered series is the collapse source.
- Reuse existing tooltip and drawing conventions where practical, including
  `_DrawnHoverCondition` for hover lifetime and source timestamps in tooltips.
  Preserve legend UI children on redraw. Host UI owns the popup widgets; they
  are not part of the mathematical calculator.

Exact public names and minimal protocol signatures should be established during
implementation; the required observable behavior is specified in the delta.

### SMA semantics

The period is a positive integer number of observed candles; reject booleans,
non-integral values, and invalid fields rather than silently coercing them.
Default to close and period 20 in the demo. For index `i`, if the last `period`
selected values are finite, output their arithmetic mean; otherwise output
NaN. Before `period` observations exist, output NaN. A timestamp gap does not
insert samples or reset the window. All timestamps remain the original candle
timestamps for calculations and tooltip data.

Computing the full history on each update is acceptable initially, but it must
be triggered by mutations, not every rendered frame. There is no constant-time
update guarantee. Full recomputation provides a correctness reference for
later optimization and naturally handles a revised forming candle.

### Synchronization and failure boundaries

Integrate with chart-owned candle mutation, not only the demo stream: prepare
derived changes from the proposed complete candle state for `set_data`,
`append_candle`/generic candle append, and
`update_last_candle`/generic latest update. Make the source, registered
indicator arrays, date caches, map/projections, and presentation publish as
one coherent operation; on validation, preparation, or publication failure,
surface the error and retain or restore the previous coherent state. Reuse
the streaming rollback mechanism rather than a post-commit callback that can
leave a new candle paired with stale values. Full data replacement continues
to follow the existing restore/reset lifecycle.

New indicators added while collapsed must be projected immediately using the
active map; no collapse toggle is needed. Edits validate and calculate before
publication, and preserve the instance's ID, legend hidden state, style,
Y-axis, active time state, and viewport. Removal unregisters the follower,
deletes its plot item, popup, and manager references, and does not change the
source or remaining indicators. Direct unsupported mutation of an indicator
must fail rather than bypass candle-derived synchronization.

Hosts serialize chart mutation and GUI editing on the existing chart-update
boundary. Do not start background tasks from the core or recompute from
render-frame callbacks.

### Demo interactions

Add a left-side indicator panel with type selection (SMA initially), period,
OHLC input, and Add. Each successful click adds a distinct instance, including
when type and parameters match an existing instance. Show validation errors
without adding a partial instance.

Each legend entry has its own menu with Edit and Remove. Edit opens a popup
prepopulated from that exact instance; Apply validates and updates it, while
Cancel leaves it unchanged. Invalid Apply keeps the popup open, reports the
error, and leaves the indicator unchanged. Menu and popup ownership must
survive candle redraws, and removing an instance must not leave callbacks or
popups targeting deleted items. Keep the existing legend-identification probe
usable; the new controls can coexist with it.

## Risks / Trade-offs

- Full-history SMA recomputation and primitive redraw can be expensive for long
  streams. Measure later; do not claim constant-time updates in this change.
- Existing candle replacement restores collapsed time; preserve that lifecycle
  rather than silently retaining an invalid old map.
- A source mutation can fail after partial UI publication. Failure-injection
  tests must cover indicator preparation and publication alongside existing
  source/follower rollback paths.
- GUI callbacks and provider consumption must use the same serialized update
  boundary; asynchronous producer work remains outside that boundary.

## Migration

Existing applications need not create indicators and retain current behavior.
No new dependency or DearCyGui changes are required.
