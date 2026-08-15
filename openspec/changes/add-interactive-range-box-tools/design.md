## Context

`examples/TA/TA_PoC_Invis_Btns.py` contains a movable, corner-resizable rectangle built from `DrawRect`, `DrawText`, and `DrawInvisibleButton` items. The interaction pattern works because the invisible items own and capture drags that would otherwise pan the plot.

Implementation SHALL follow the repository guidance in `.github/skills/technical-indicator-drag-tools/SKILL.md`. That skill defines the approved DearCyGui interaction pattern, handler and cursor behavior, cumulative drag-delta rules, hit-region ordering, geometry synchronization, and the boundary between project-owned code and the vendored `dearcygui.utils.draw_draggable.py` reference.

DearCyFi now owns the selected collapse source and one active `GapCollapsedTimeMap`. Candle rendering already separates original `source_dates` from mutable plotted dates. A production drawing tool must preserve the same distinction: a box represents real timestamps and prices even when its rendered X coordinates have been compressed.

The demo also needs callback-friendly chart commands that can be wired to controls in the same sidebar as data and collapse controls. Those controls are tool commands, not market-data providers, so they do not belong in the data-widget registry.

## Goals / Non-Goals

### Goals

- Promote the PoC interaction pattern into a reusable package-owned range box.
- Introduce the smallest useful chart-tool lifecycle and anchor vocabulary needed by later Fibonacci, trend, and multi-anchor pattern tools.
- Preserve canonical source-time anchors across collapse, restore, and candle reload operations.
- Provide simple chart-level add/remove-all commands for host controls.
- Establish geometry and lifecycle hooks that future Fibonacci, labels, and candle calculations can reuse.
- Keep plot pan and zoom available outside semantic box hit regions.

### Non-Goals

- Fibonacci retracement levels or specialized Fibonacci interaction.
- Corner date/price label rendering.
- Price-volume, volume-profile, or other candle aggregation.
- Persistence, serialization, selection sets, undo/redo, or keyboard deletion.
- A general plugin system for technical-analysis tools.
- Pattern recognition, automatic anchor placement, or a shared renderer for unrelated tool shapes.

## Decisions

### Decision: Define a Small Generic Tool Contract Before the First Concrete Tool

Do not make rectangle bounds the inheritance model for every future technical-analysis tool. Fibonacci retracements can use two anchors, while head-and-shoulders annotations and other chart patterns need a variable number of named points and different drawing primitives.

Add a lightweight package-owned contract, named `InteractiveChartTool` or equivalent, that defines only lifecycle and coordinate responsibilities shared by all interactive tools:

```python
class InteractiveChartTool(Protocol):
    tool_id: str
    tool_kind: str

    def refresh_projection(self) -> None: ...
    def dispose(self) -> None: ...
```

Concrete tools own their drawing children, interaction regions, semantic geometry, and tool-specific mutation rules. The first implementation may use an abstract base class instead of a protocol when shared chart/projection wiring removes real duplication, but it SHALL NOT require future tools to inherit rectangle geometry or corner handle behavior.

Canonical points use a small immutable source-space value type:

```python
@dataclass(frozen=True)
class ToolAnchor:
    source_x: float
    y: float
```

Each concrete tool assigns semantic names or roles to its anchors. A range box exposes two normalized corner anchors through `RangeBoxGeometry`; a future Fibonacci tool may expose `start` and `end`; a head-and-shoulders annotation may expose named shoulder, head, and neckline anchors. This provides a common coordinate vocabulary without imposing one geometry container on every tool.

`tool_id` is unique within one chart and stable for the tool's lifetime. `tool_kind` is a short semantic identifier such as `"range-box"`. Identity supports later selection, targeted removal, serialization, and command routing, but those features remain out of scope.

### Decision: Separate Tool Rendering from Chart Collection Ownership

Add a package-owned `RangeBoxTool` that implements the generic lifecycle contract and owns one box's geometry, drawing items, hit regions, drag state, and callbacks. `DearCyFi` owns one ordered collection of generic interactive tools and exposes filtered box access plus the requested conveniences:

```python
@property
def tools(self) -> tuple[InteractiveChartTool, ...]: ...

def add_box(
    self,
    sender=None,
    app_data=None,
    user_data=None,
    *,
    p1: tuple[float, float] | None = None,
    p2: tuple[float, float] | None = None,
    on_geometry_changed=None,
    **style,
) -> RangeBoxTool: ...

def remove_all_boxes(self, sender=None, app_data=None, user_data=None) -> None: ...

def get_box_snapshots(self) -> tuple[RangeBoxSnapshot, ...]: ...

def print_boxes(self, sender=None, app_data=None, user_data=None) -> str: ...

@property
def boxes(self) -> tuple[RangeBoxTool, ...]: ...
```

The chart uses an internal registration path for concrete tools so future `add_fibonacci(...)` or `add_pattern(...)` commands reuse collection ownership and lifecycle refresh rather than adding parallel lists. That internal path is not a public plugin API in this change.

The optional callback positional arguments allow direct DearCyGui button wiring. Programmatic callers use keyword geometry and receive the created tool. `remove_all_boxes()` removes only tools whose kind is `"range-box"` and is idempotent; future non-box tools would remain untouched. Generic remove-one and remove-all-tool commands are deferred until selection and command semantics are designed.

`get_box_snapshots()` returns immutable diagnostic snapshots containing each box's `tool_id`, `tool_kind`, canonical source-time/price geometry, and current rendered plot geometry. `print_boxes()` formats those snapshots deterministically, prints the text to the console, reports it through the chart status callback, and returns the same text for tests and non-GUI callers. An empty collection produces an explicit `No range boxes.` message.

The diagnostic output is for inspection, not serialization. Including both coordinate spaces makes collapse behavior visible and avoids presenting compressed plot X values as real timestamps. A future persistence format must be separately versioned and based on canonical source geometry.

When `p1` and `p2` are omitted, `add_box()` derives a practical initial rectangle from the currently visible X/Y range and converts its X corners to source time. If the visible range is not usable, it falls back to the loaded candle extents. Adding a box without loaded candles fails clearly because the initial capability is candle-associated.

### Decision: Keep Canonical Source Geometry

Each tool stores canonical geometry separately from rendered geometry:

```python
@dataclass(frozen=True)
class RangeBoxGeometry:
    source_x1: float
    source_x2: float
    y1: float
    y2: float
```

`RangeBoxGeometry` is a box-specific convenience composed from the common source-space anchor vocabulary; it is not the base geometry for all future tools. X values are real Unix timestamps. Y values are coordinates on the box's assigned price axis. The tool normalizes public bounds unless inversion is explicitly supported by a later capability.

For rendering:

- without an active collapse map, plotted X equals source X;
- with an active map, source X is projected through `GapCollapsedTimeMap.project()` using a documented annotation policy;
- while dragging on a collapsed chart, plotted X is converted back through `GapCollapsedTimeMap.expand()` before canonical geometry is committed.

This is deliberately different from registering the two box anchors as a time series. Annotation anchors must not influence collapse-map construction or pretend to be observations. The chart invokes a lightweight box refresh after collapse, restore, and candle replacement.

The initial in-gap annotation policy is `next`, matching the chart's default follower policy. The policy is stored on the tool so a later change can expose alternatives without changing geometry ownership.

### Decision: Associate with Candles Without Implementing Aggregation

Each managed box holds a non-owning association to the chart and resolves its current `PlotCandleStick` through that chart rather than retaining a stale candle object after data replacement. The tool exposes two high-level callback phases:

- `on_geometry_changing(tool, geometry)` during interactive movement for live readouts and previews;
- `on_geometry_committed(tool, geometry)` once on release or programmatic commit for expensive calculations and future undo history.

Callbacks receive an immutable source-space `RangeBoxGeometry` snapshot and do not expose internal buttons or handlers. Public source geometry is sufficient for later code to:

1. select candles whose `source_dates` fall between the X anchors;
2. optionally filter by the Y bounds;
3. calculate price-volume or another statistic; and
4. format corner dates using chart time-format settings.

The first implementation does not expose a premature aggregation API. Candle selection and aggregation semantics need separate decisions about inclusive boundaries, partial candle overlap, price choice, and volume treatment.

Programmatic geometry assignment uses the same validation, projection refresh, and committed notification path as pointer interaction. This prevents future tool panels, persistence loaders, or tests from bypassing invariants.

### Decision: Retain Invisible-Button Interaction Ownership

The production tool follows the proven DearCyGui pattern:

- one visible `DrawRect` and optional label/handle drawings;
- a body `DrawInvisibleButton` for movement;
- four corner `DrawInvisibleButton` items for two-axis resizing;
- cumulative drag deltas applied to backup geometry captured on the first dragging callback;
- one geometry synchronization method that updates visible and invisible children together;
- screen-space hit sizing through `min_side`;
- cursor handlers attached to invisible buttons;
- callbacks invoked after internal state mutation and without holding internal locks.

Broad hit regions are created before corner hit regions so corners win overlap priority. The initial production tool retains the PoC's four-corner scope; edge handles can be added later if needed.

### Decision: Put Demo Commands in a Dedicated Control Group

Add a `Technical Analysis` collapsing header in the demo sidebar near `Collapsing Controls`. It contains `Add Box`, `Print Boxes`, and `Remove All Boxes` buttons wired to the chart methods. It is not registered in `DATA_WIDGETS`, because it neither discovers nor loads data and must not acquire provider lifecycle semantics.

The Add command uses chart-derived default geometry, making it useful without a separate drawing mode. Multiple clicks create independent boxes. Print Boxes reports stable IDs and canonical/rendered coordinates for every box. Remove All disposes every box drawing and interaction item and leaves candle/econometric series untouched.

## Risks / Trade-offs

- `GapCollapsedTimeMap.expand()` has defined bridge and boundary behavior that may snap an anchor dragged into a retained collapse bridge. The tool uses that same behavior as cursor labels and axis ticks, keeping one interpretation of collapsed time.
- Re-rendering many boxes during collapse adds work. Box refresh is lifecycle-driven rather than per-frame, and shared handler lists should be used if profiling shows per-instance handlers are material.
- A large body hit region can reduce plot-pan access. The body region should be inset and handles should remain small, leaving the surrounding plot interactive.
- Candle replacement can move the useful data range away from existing source anchors. Boxes preserve their source geometry rather than silently changing analytical meaning; hosts can call `remove_all_boxes()` when replacement should clear annotations.
- A base class can become a premature hierarchy. The shared contract is therefore limited to identity, source-coordinate projection lifecycle, and disposal; drawing composition and semantic geometry stay concrete.

## Migration Plan

1. Add and export the package-owned anchor/lifecycle contract, box geometry, and range-box class.
2. Add generic chart collection ownership, filtered box access, and lifecycle refresh calls.
3. Add unit tests for geometry conversion and chart commands before demo wiring.
4. Wire the demo controls and manually verify move, resize, collapse, restore, add-many, and remove-all behavior.
5. Keep the PoC as a focused reference until the production demo path is validated; do not import it from package code.

## Open Questions

- Should a later annotation persistence feature preserve boxes across an entirely new symbol load, or should the demo clear them by default?
- Should future candle selection include candles by center timestamp only or include bodies/wicks that overlap the box boundary?
- Which selection and command model should introduce targeted removal and keyboard interaction across heterogeneous tools?
