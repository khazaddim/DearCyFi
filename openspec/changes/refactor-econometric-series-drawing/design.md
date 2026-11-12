## Context

The current econometric composite owns a native line, an optional native scatter plot, and a separate interaction layer. A legend click only controls the line. The candle renderer instead owns its drawing primitives as children of one legend-enabled `DrawInPlot`.

## Goals / Non-Goals

- Group the line, optional markers, and tooltip targets under one legend item.
- Preserve data validation, fitting, axes, source and plot dates, and collapse coordination.
- Provide explicit styling for the supported line and circular markers.
- Do not add a general-purpose geometry framework, streaming renderer, or changes to candles, volume, or gap detection.

## Decisions

- Use one legend-enabled `DrawInPlot` for the econometric line segments, optional observation markers, and tooltip hit regions. Do not retain a separate visible or interactive plot item.
- Draw segments only between consecutive finite observations; there is no interpolating alternative because native `skip_nan` is not supported. Preserve original source dates separately from plotted dates, including through updates and collapse/restore.
- Keep marker dimensions stable in screen space, and use the selected `(X1, Y1/Y2/Y3)` axes for the entire drawing item. Every finite observation must contribute to fitting, including isolated observations with markers and tooltips disabled. Empty or entirely non-finite data must not supply invalid bounds, and hidden series must not affect fitting. Verify DearCyGui's actual fitting behavior; if needed, implement a synchronized fitting mechanism without another independently visible legend item.
- Replace `line_kwargs` and `marker_kwargs` with explicit line color, line thickness, marker color, and marker radius options. Document their names, units, defaults, and migration examples. Line thickness and marker radius are screen-space sizes. Choose defaults that retain a usable demo appearance. Reject legacy kwargs clearly rather than silently discarding native-specific options such as themes or `skip_nan`.
- Treat direct access to the existing native `line` and `markers` objects as a breaking change. Do not substitute misleading stand-ins that appear to preserve their native APIs.
- Preserve the constructor's data, label, `markers` boolean, tooltip, formatter, and axis arguments, along with data properties and the update, plot-date, and restore methods. The `markers` constructor argument is distinct from the removed native object attribute.
- Rebuild primitive and interaction children after data or plotted-date updates, without changing the registered series identity, selected axes, or legend visibility. Validate before mutating data or drawing state.
- Hiding a series must suppress its hover targets and dismiss an active observation tooltip. Replacing a target must also clear any active tooltip associated with it. Verify actual legend interaction rather than assuming legend visibility and an item's `show` property are interchangeable.

### Verified mechanisms (custom DearCyGui build)

- When ImPlot's legend hides a `DrawInPlot`, `BeginItem` returns false and no children are drawn. Children are skipped without updating their item state, so a hovered `DrawInvisibleButton` can keep a stale `hovered` flag. `plotElement` exposes no Python `handlers` or `state`, so the series cannot observe legend hover itself.
- Tooltip lifetime: when an observation is hovered, the series attaches a private `CustomHandler` to that button and uses the same handler as the tooltip's `condition_from_handler`. Its `run` records that the button was drawn this frame, and `check_status` consumes that record and requires `hovered`. A legend-hidden target therefore closes its tooltip immediately. The handler is removed when the tooltip is cleared on lost hover or rebuild. Tooltips are parented to the plot's parent so they are never drawn in the series' legend popup.
- Fitting: `DrawInPlot` enables plot fitting for its children only while it is drawn, and primitive coordinates are fitted as they are drawn. Childless invisible buttons never fit. Isolated finite observations without markers get a zero-radius transparent `DrawCircle` anchor. A rendered probe confirmed that isolated points fit, all-NaN data supplies no bounds, a legend-hidden series is excluded, and changing the label keeps the series hidden (the ImPlot ID is `label###uuid`).
- Sizes: negative `DrawCircle` radius and negative `DrawPolyline` thickness are unscaled screen pixels, so the public options are stored positive and negated internally.

## Alternatives

- Synchronize the existing native items: retains native drawing but leaves several plot items and requires explicit visibility and interaction synchronization.
- Draw only the markers as primitives: still separates them from the native line and requires visibility synchronization.
- Draw all series elements in one legend-enabled item: selected for shared ownership and visibility.

## Risks

- Primitive rendering can have greater per-observation overhead than native plotting. The intended initial use remains low-frequency econometric data; validate a representative demo dataset.
- A drawing item may behave differently from native plot items for axis fitting, clipping, styling, and NaN handling. Test these behaviors explicitly rather than assuming equivalence. If the single-item contract cannot be achieved with the supported DearCyGui build, stop and revise the proposal before implementation.
- Hiding a series must prevent hover callbacks as well as remove visible primitives. Verify the actual legend interaction in a running viewport, not only the item hierarchy.
- Archive the completed `add-econometric-series-collapse-source` change before archiving this change so that the modified requirements exist in the baseline. Preserve the independently proposed axis-assignment requirements.

## Rollout

Approve this change before implementation. First verify the drawing, legend, tooltip, and fitting mechanisms with the custom DearCyGui build, then implement and test the renderer. Document the breaking migration before release.
