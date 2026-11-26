## Context

`PlotCandleStick` is a `dcg.DrawInPlot` composite with an internal `dcg.PlotDigital` volume series. `PlotEconometricSeries` owns a `dcg.PlotLine`, optional `dcg.PlotScatter`, and drawing-based tooltip hit regions. These elements currently use DearCyGui's default `(X1, Y1)` axis pair.

DearCyFi collapse coordination transforms only X coordinates. A Y-axis selection must therefore leave every series on `X1` while consistently routing all of its Y coordinates to one of DearCyGui's `Y1`, `Y2`, or `Y3` axes.

The optional label-overlap and date-context diagnostic overlays currently reserve `Y2` and configure it as a hidden, locked 0-1 scale when enabled.

## Goals / Non-Goals

### Goals

- Allow candle and econometric composites to select `Y1`, `Y2`, or `Y3` explicitly.
- Keep all visual and interaction elements in each composite aligned to the same axis pair.
- Preserve existing callers through a `Y1` default.
- Demonstrate independently readable price and econometric scales.
- Preserve all existing collapse and restoration behavior.

### Non-Goals

- Independent X-axis assignment or multiple collapse maps.
- Automatic axis selection based on value ranges.
- Automatic axis labels, units, colors, or side placement in the reusable classes.
- Assigning candle volume to an axis separate from its candle composite.
- Reworking the diagnostic overlay's `Y2` reservation.

## Decisions

### Decision: Accept a Y-Axis Enum, Not an Arbitrary Axis Pair

Add `y_axis: dcg.Axis = dcg.Axis.Y1` to `PlotCandleStick` and `PlotEconometricSeries`, and expose the same selection through `DearCyFi.set_data(...)`. The implementation will validate that the value is one of `dcg.Axis.Y1`, `dcg.Axis.Y2`, or `dcg.Axis.Y3` and derive `axes=(dcg.Axis.X1, y_axis)` internally.

This keeps the shared time-axis invariant explicit and prevents a series from being assigned to an X axis that DearCyFi's locator and collapse coordination do not manage.

### Decision: Bind the Complete Composite

For candles, the selected pair applies to the `PlotCandleStick` `DrawInPlot` and its internal volume `PlotDigital` series.

For econometric data, the pair applies to the line, optional markers, and a `DrawInPlot` interaction container that owns the invisible tooltip buttons. A bare `DrawingList` cannot select plot axes, so the interaction layer must be nested under that axis-aware container.

Each class will expose its selected `y_axis` for inspection. Complete data updates retain the current assignment. If `DearCyFi.set_data(...)` is called with a different axis for an existing candle series, the composite and its volume element move together before fitting or rendering subsequent data.

### Decision: Keep Axis Presentation in the Host

The reusable renderers select an axis but do not enable, label, fit, or style it. Those are chart-level presentation decisions.

The demo will keep prices on `Y1`, configure `Y3` with an econometric label, enable it, create the weekly series with `y_axis=dcg.Axis.Y3`, and fit `Y1` and `Y3` independently after loads. `Y2` remains available to the existing optional diagnostics. Documentation will note that consumers assigning data to `Y2` should not enable those diagnostics because the diagnostic feature intentionally reconfigures that axis.

### Decision: Preserve Keyword-Override Clarity

`line_kwargs`, `marker_kwargs`, and `volume_kwargs` remain styling/configuration extension points, but they may not override `axes`. The explicit `y_axis` argument is the single source of truth for composite alignment. Conflicting `axes` entries will be rejected with a clear error rather than allowing partially split composites.

## Risks / Trade-offs

- Consumers must enable and fit secondary axes themselves. This avoids surprising chart-level mutations by a series constructor and is demonstrated in the demo.
- Reserving one axis for optional diagnostics leaves only two user scales while diagnostics are enabled. The demo uses `Y3` for econometric values to avoid that conflict.
- Moving existing candle elements between axes during a later `set_data(...)` call depends on DearCyGui's mutable `axes` property. Focused runtime tests will verify both initial and replacement assignments against the installed DearCyGui version.

## Migration Plan

1. Add shared validation behavior locally in each renderer or a small internal helper if duplication warrants it.
2. Add the axis argument and composite propagation to candle and econometric renderers.
3. Route candle axis selection through `DearCyFi.set_data(...)`.
4. Update focused tests and run the existing collapse suite.
5. Configure `Y3` in the demo and manually verify independent fitting before and after collapse.
6. Document the public arguments and host-owned axis setup.
