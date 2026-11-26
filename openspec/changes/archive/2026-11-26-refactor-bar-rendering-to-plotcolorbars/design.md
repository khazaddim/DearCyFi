## Context

This branch consumes a custom DearCyGui build (`khazaddim/DearCyGui`) that introduces `PlotColorBars` as a native series in `dearcygui.plot`. The implementation computes anchor start values from current plot limits during draw (`baseline`, `axis_min`, `axis_max`), supports `value_space` (`data` or `normalized`), and renders per-bar fill and optional line colors directly through the plot draw list.

Current DearCyFi bar behavior is split:

- Horizontal liquidity bars use `DrawInPlot` + `DrawRect` primitives and are manually repositioned via `AxesResizeHandler` callback logic.
- Candle volume bars use `PlotDigital` and cannot carry per-bar up/down fill color semantics.

## Goals / Non-Goals

### Goals

- Use `PlotColorBars` as the default bar primitive for horizontal liquidity bars and candle volume bars.
- Remove callback-driven bar repositioning for horizontal bars.
- Enable up/down volume coloring tied to candle direction.
- Preserve existing data/collapse integration and axis assignment behavior.
- Keep updates smooth when bar counts change at runtime.

### Non-Goals

- Correcting all zoom-dependent bar sizing behavior in this first stage.
- Implementing volume-weighted price sampling or deriving horizontal bars from production market data.
- Replacing or otherwise changing label-extent, overlap, date-context, or gap-collapse diagnostics.
- Modifying time-collapse map semantics or locator behavior.
- Introducing additional plotting dependencies beyond custom DearCyGui.

## Decisions

### Decision: Horizontal Bars Use PlotColorBars Axis Anchoring

`DearCyFi.load_horizontal_bars(...)` will instantiate a `dcg.PlotColorBars` series with:

- `horizontal=True`
- `anchor="axis_max"`
- `ignore_fit=True`

The right-edge anchor is resolved each render from current axis limits, removing the need to recompute rectangle coordinates inside `axes_resize_callback`.

### Decision: Candle Volume Moves From PlotDigital To PlotColorBars

`PlotCandleStick` will replace its internal `PlotDigital` volume series with `PlotColorBars` configured in vertical mode and bound to the same `(X1, y_axis)` pair as the candle composite.

Default geometry and normalization policy:

- `anchor="axis_min"` keeps volume bars attached to the bottom of the selected Y-axis viewport.
- `value_space="normalized"` makes bar height relative to the current Y-axis span rather than raw price-axis units.
- `ignore_fit=True` prevents volume bars from changing price-axis fitting.
- Non-negative volume magnitudes are normalized to a stable input range before assignment, with the largest non-zero volume mapping to `normalized_max_fraction` of the visible plot height and zero/all-zero inputs handled without division errors.

These defaults are intended to reproduce `PlotDigital`'s visual independence from Y-axis zoom while adding per-bar colors. Exact width, height fraction, and normalization details will be compared with the existing `PlotDigital` appearance and tuned during implementation and demo validation.

Color policy:

- Default: up-volume bars use bull color and down-volume bars use bear color.
- Optional override: `volume_kwargs` can provide single-color or per-bar colors.

### Decision: Keep User-Facing API Mostly Stable

Existing public methods remain:

- `DearCyFi.load_horizontal_bars(...)`
- `PlotCandleStick(..., volume_kwargs=...)`

Behavior shifts from callback-updated geometry to native anchored rendering, but caller signatures should remain compatible where practical.

### Decision: Retire DCG_Bar_Utils Runtime Dependency

`core.py` will stop importing `PlotHorizontalBars` and rely on `PlotColorBars` directly.

`DCG_Bar_Utils.py` will remain temporarily as a deprecated compatibility module for downstream scripts. DearCyFi production paths and the demo will no longer use it. Its deprecation notice will direct callers to `dcg.PlotColorBars`; removal can be considered in a later breaking change.

### Decision: Preserve Existing Diagnostic Paths

The label-extent, overlap, and date-context diagnostic overlays will remain on `PlotDigital` and their fixed hidden Y2 axis. Gap-collapse diagnostics and testing behavior will also remain unchanged.

These diagnostics are important validation tools and are outside this first-stage renderer migration. A later proposal may evaluate richer diagnostic rendering independently after the production bar paths are stable.

### Decision: First-Stage Sizing Is Approximate

This change establishes `PlotColorBars` as the default renderer for vertical volume bars and price-sampled horizontal bars. Exact apparent sizing of price-sampled horizontal bars across every zoom level is not a completion criterion for this stage; current horizontal sizing behavior is already approximate.

The horizontal implementation will preserve stable, usable defaults and avoid regressions that make bars disappear or dominate the plot. More precise horizontal sizing and normalization will be designed alongside actual volume-weighted price sampling in a follow-up change. Candle-volume normalization is part of this change and must preserve a bottom-anchored, screen-relative appearance under Y-axis zoom.

### Decision: Runtime Guard For PlotColorBars Availability

Because this repo branch depends on the custom DearCyGui build, DearCyFi should fail fast with a clear error if `dcg.PlotColorBars` is missing, rather than silently falling back to a slower legacy path.

## Risks / Trade-offs

- The custom DearCyGui API may continue evolving while DearCyFi code stabilizes; tests must pin expected properties (`anchor`, `value_space`, `normalized_max_fraction`).
- Color-array length validation in `PlotColorBars` is strict; count-changing updates need order-safe assignment patterns to avoid transient mismatches.
- Normalizing volume by the current data maximum can change relative heights when data is replaced or appended; visual comparison and update tests must establish acceptable behavior.
- If users run DearCyFi with upstream DearCyGui, runtime guard behavior becomes a deliberate compatibility break on this branch.

## Migration Plan

1. Introduce internal helper methods for building and updating `PlotColorBars` with count-safe assignment ordering.
2. Migrate horizontal bars in `core.py` and remove callback reposition calls for that feature.
3. Migrate candle volume path in `DCG_Candle_Utils.py` with normalized, axis-min-anchored defaults and compare its pan/zoom appearance against the existing `PlotDigital` path.
4. Deprecate `DCG_Bar_Utils.py` while removing it from production and demo imports.
5. Update demo controls to showcase normalized vs data mode for horizontal overlays and visible up/down volume colors.
6. Update tests for axis propagation, color behavior, normalized volume geometry, Y-axis zoom behavior, and count-changing updates while retaining existing diagnostic and gap-collapse coverage.
7. Document custom DearCyGui requirements, approximate first-stage sizing, and deferred volume-weighted price sampling work.
