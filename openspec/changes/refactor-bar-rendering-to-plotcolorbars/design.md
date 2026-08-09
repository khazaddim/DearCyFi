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

- Rewriting label-overlap/date-context diagnostics in this change.
- Replacing non-bar `PlotDigital` usages outside DearCyFi bar workflows.
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

`DCG_Bar_Utils.py` will be either:

- Removed if unused, or
- Reduced to a thin compatibility shim with deprecation guidance.

Preferred approach is removal only after confirming no internal imports remain.

### Decision: Runtime Guard For PlotColorBars Availability

Because this repo branch depends on the custom DearCyGui build, DearCyFi should fail fast with a clear error if `dcg.PlotColorBars` is missing, rather than silently falling back to a slower legacy path.

## Risks / Trade-offs

- The custom DearCyGui API may continue evolving while DearCyFi code stabilizes; tests must pin expected properties (`anchor`, `value_space`, `normalized_max_fraction`).
- Color-array length validation in `PlotColorBars` is strict; count-changing updates need order-safe assignment patterns to avoid transient mismatches.
- If users run DearCyFi with upstream DearCyGui, runtime guard behavior becomes a deliberate compatibility break on this branch.

## Migration Plan

1. Introduce internal helper methods for building and updating `PlotColorBars` with count-safe assignment ordering.
2. Migrate horizontal bars in `core.py` and remove callback reposition calls for that feature.
3. Migrate candle volume path in `DCG_Candle_Utils.py`.
4. Update demo controls to showcase normalized vs data mode for horizontal overlays and visible up/down volume colors.
5. Update tests for axis propagation, color behavior, and count-changing updates.
6. Document custom DearCyGui requirement and bar behavior changes in README/demo notes.

## Open Questions

- Should `DCG_Bar_Utils.py` be deleted in this same change or kept temporarily as a deprecated compatibility layer for downstream scripts?
- Should diagnostic `PlotDigital` overlays move to `PlotColorBars` in a follow-up change for consistency, or remain as-is due different visual intent?
