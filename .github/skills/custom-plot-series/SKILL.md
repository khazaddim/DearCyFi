---
name: custom-plot-series
description: "Use when: designing, implementing, reviewing, or testing a new DearCyFi plot series built from DearCyGui drawing primitives (DrawInPlot subclasses) such as econometric, options, liquidity, overlay, or other composite/exotic series; fixing legend hide/show, tooltip, axis-fit, Y-axis assignment, or time-collapse behavior of a custom series; or deciding between native ImPlot items (PlotLine/PlotScatter/PlotColorBars) and primitive drawing."
argument-hint: "New or changed DearCyFi custom series"
---

# Custom Plot Series

## When To Use

Use this skill when creating or changing a DearCyFi series that draws more than one kind of shape (line + markers, bodies + wicks, bands, labels, hit regions), or any series that must hide, fit, collapse, and tooltip as a single unit. Reference implementations:

- `src/dearcyfi/econometric_series.py` — `PlotEconometricSeries` (polyline runs, optional markers, tooltip hit regions, drawn-hover tooltip condition). This is the canonical template.
- `src/dearcyfi/DCG_Candle_Utils.py` — `PlotCandleStick` (wicks, bodies, buttons). Its volume bars are a separate `PlotColorBars` item and therefore do **not** follow its legend toggle — a known limitation, not a pattern to copy.

DearCyGui internals referenced below live in the custom source tree `C:\Users\khazy\OneDrive\Documents\DearCyGui-custom\dearcygui\` (`plot.pyx`, `draw.pyx`, `widget.pyx`, `core.pyx`, `imgui.pxd`). The `.pyx` files are not in site-packages; never edit `.venv*` files.

## Core Rule: One Series = One Legend Item

If a series is composed of several native plot items (e.g. `PlotLine` + `PlotScatter` + a `DrawInPlot` of buttons), the legend only controls the item that owns the entry; the other parts stay visible. To make the legend hide/show everything:

- Subclass `dcg.DrawInPlot` and set `self.no_legend = no_legend` (default `False`) after `super().__init__`; `DrawInPlot` hides itself from the legend by default.
- Draw every visual and interactive part as **children** of that item.
- When ImPlot's legend hides the item, `BeginItem` returns false and no children are drawn, so all parts disappear together and stop contributing to fit.

Use a native ImPlot item (`PlotLine`, `PlotColorBars`, ...) only for a single-shape series where native features (e.g. performance on very large arrays) matter more than composite behavior.

## Class Template

```python
class PlotMySeries(dcg.DrawInPlot):
    def __init__(self, context, *, dates, values, label="My Series",
                 source_dates=None, tooltip=True, y_axis=dcg.Axis.Y1,
                 line_color=..., line_thickness=1.5, no_legend=False, **kwargs):
        # 1. Reject unsupported/legacy kwargs and "axes" (use y_axis) BEFORE super().__init__.
        # 2. Validate y_axis and screen sizes; build validated array copies.
        super().__init__(context, label=str(label), axes=(dcg.Axis.X1, y_axis), **kwargs)
        self.no_legend = no_legend
        # 3. Store state (_plot_dates, _source_dates, values, styles, tooltip bookkeeping).
        self.render()

    def render(self):            # rebuild ALL children from current state
        self._clear_active_tooltip()
        self.children = []
        with self:
            ...                  # Draw* primitives + DrawInvisibleButton hit regions
        ...                      # attach shared hover handlers to buttons

    def update_all(self, *, dates, values, source_dates=None, label=None): ...
    def set_plot_dates(self, dates): ...       # time-collapse contract
    def restore_source_dates(self): ...        # time-collapse contract
    # read-only copies: source_dates, plot_dates, values; plus y_axis
```

Rules:

- **Do not assign `self.context`** (native, read-only). **Do not shadow `label`** — use the native property; its ImPlot ID is `label###uuid`, so renaming keeps the legend hidden state.
- **Validate before mutating.** Compute validated copies first; only then assign state and call `render()`. A failed update must leave data and children untouched.
- `render()` is the single place that builds children; every data, plot-date, or style change calls it. Rendering never changes `show` or legend visibility.
- `plotElement`/`DrawInPlot` exposes no Python `handlers` or `state`; do not attach handlers to the series itself.
- The legend swatch color comes from ImPlot's colormap, not from your primitives' colors.

## DearCyFi Integration Contract

`DearCyFi.register_time_series(series_id, series, in_gap=..., replace=...)` in `src/dearcyfi/core.py` duck-types the series. It must provide:

- `source_dates` — original timestamps (never mutated by collapse).
- `set_plot_dates(dates)` — apply collapsed/transformed X coordinates (same length as `source_dates`), then `render()`.
- `restore_source_dates()` — `set_plot_dates(source_dates)`.

Keep source and plotted dates separate. Tooltips must show **source** dates, never synthetic collapsed X; store source data in each hit region's `user_data`.

Hosts create the series inside `with chart:` and own axis presentation (`chart.Y3.enabled/label/fit()`). Support `y_axis` in `Y1/Y2/Y3` only; X is always `X1`.

## Primitive Facts (verified on the custom build)

| Need | Primitive | Notes |
| --- | --- | --- |
| Connected line | `DrawPolyline(points=..., thickness=-px)` | One polyline per run of consecutive finite points; split runs at NaN. Never interpolate. |
| Constant-size marker | `DrawCircle(radius=-px, fill=color, thickness=-1)` | Negative radius = unscaled screen pixels. |
| Segment | `DrawLine` | Positive thickness scales with zoom; negative = screen px. |
| Rectangle body | `DrawRect(pmin, pmax, fill=...)` | Coordinate space. |
| Hover target | `DrawInvisibleButton(p1=pt, p2=pt, min_side=8, button=0, user_data=...)` | Childless buttons do **not** contribute to axis fit. |

Sizing comes from `imgui.pxd` `get_scaled_thickness`/`get_scaled_radius`: positive = coordinate/zoom-scaled, negative = screen pixels. Expose **positive** screen-pixel options publicly, validate `> 0` and finite, and negate internally.

Finding runs of consecutive finite observations:

```python
finite = np.isfinite(plot_dates) & np.isfinite(values)
idx = np.flatnonzero(finite)
runs = np.split(idx, np.flatnonzero(np.diff(idx) != 1) + 1) if idx.size else []
```

## Axis Fitting

- `DrawInPlot.draw` sets `viewport.plot_fit = FitThisFrame()` before drawing children, so every drawn primitive coordinate is auto-fitted. A legend-hidden item draws nothing and never fits. `ignore_fit=True` opts out.
- If a finite point would otherwise produce no fitting primitive (e.g. an isolated point with markers off), add an invisible anchor: `DrawCircle(center=pt, radius=0, color=0, fill=0)`.
- Empty or all-NaN data must create no primitives, so no invalid bounds are supplied.

## Tooltips (critical lifetime gotcha)

When the legend hides a `DrawInPlot`, its children are **skipped without updating state**: a button can keep a stale `hovered=True`, so a plain `Tooltip(target=button)` may stay open for a hidden series.

Use the shared `_DrawnHoverCondition` from `src/dearcyfi/_series_tooltips.py`, as used by both `PlotEconometricSeries` and `PlotCandleStick`:

1. Attach shared `GotHoverHandler` → `_tooltip_handler` and `LostHoverHandler` → `_tooltip_lost_handler` to all buttons.
2. On hover, clear any active tooltip, create a `_DrawnHoverCondition` (`dcg.CustomHandler`), append it to that button's handlers, and pass it as the tooltip's `condition_from_handler`. Its `run()` marks "drawn this frame"; `check_status()` consumes the mark and requires `item.state.hovered`. If the button is not drawn, the tooltip closes immediately.
3. Parent the tooltip to `self.parent.parent` (outside the series). Widget children of a legend-enabled `DrawInPlot` are rendered inside its **legend popup**.
4. `_clear_active_tooltip()` deletes the tooltip and removes the condition handler from its target; call it from `render()` and on lost hover. Keep at most one active tooltip per series.

Reuse this shared condition rather than re-implementing it. Both candle and econometric tooltips use it; candle volume remains a separate plot item.

## Styling API

Expose explicit, documented options (e.g. `line_color`, `line_thickness`, `marker_color`, `marker_radius`) instead of forwarding `**kwargs` dicts to internal objects. Internal primitives are implementation details; do not expose them as public attributes. Forward remaining kwargs only to `DrawInPlot` (`show`, `ignore_fit`, ...). When removing an old option, raise a `ValueError` naming it and its replacement.

## Exotic Series Notes (e.g. options on the underlying's axes)

- Use one `DrawInPlot` per independently toggleable series. If two parts must toggle separately (e.g. candle volume), make them separate series items.
- Anchoring/pinning to another series (e.g. starting an option's price at the underlying's X at entry) belongs in the adapter or in explicit constructor inputs. Store anchor data as source data, derive plot coordinates in `render()`, and keep `set_plot_dates` semantics consistent so time collapse moves both series together.
- Do not add gap-aware econometric behavior incidentally; preserve timestamps and gaps at the data boundary.

## Testing

Unit tests run without a viewport (`.\.venv-dcg\Scripts\python.exe -m pytest ...`, via execution_subagent):

- Inspect `series.children` by type (`DrawPolyline.points`, `DrawCircle.center/radius/fill`, `DrawInvisibleButton.p1/user_data`).
- Cover: NaN run breaks, isolated anchors, empty/all-NaN data, marker/tooltip toggles, styles, validation before mutation, `update_all` replacing children and keeping `show`, collapse/restore with source-date `user_data`, all Y axes, legacy/`axes` rejection, and the drawn-hover condition (`run` then `check_status` is true once, then false).
- Related suites: `tests/test_series_axis_assignment.py`, `tests/test_collapse_coordination.py`, `tests/test_toy_econometric_widget.py`.

Rendered probes for legend toggle, fit, and tooltips — write a temporary script outside the repo (session `files/`) rather than modifying the demo:

- Use `C.viewport.initialize(..., visible=False)` so the real OS mouse cannot override injected input.
- Re-inject `C.inject_mouse_pos(x, y)` before every `render_frame()`; use `dcg.MouseButton.LEFT` with `inject_mouse_down/up`.
- Hover interior points (points at plot corners can be clipped). Read button screen rects from `button.state.pos_to_viewport` / `rect_size` after a few frames.
- Find the legend entry by scanning clicks near the plot's top-left; detect hiding with a `CustomHandler` whose `run()` counts draws of a child button (the count stops when hidden).
- Check fit with `plot.X1.fit(); plot.Y1.fit()` and read `plot.X1.min/max`; include a second visible series so hidden-series exclusion is observable.
- Delete the probe afterward, then confirm manually in the demo (`run_demo_with_custom_dcg.ps1`).

## Process

Composite series changes are usually architectural or breaking: follow `openspec/AGENTS.md` (proposal → approval → implement → check off `tasks.md` → `openspec validate <change> --strict --no-interactive`). Update the README series section with options, units, defaults, and migration notes.
