## 1. Renderer Axis Assignment

- [ ] 1.1 Add validated `y_axis` selection to `PlotCandleStick`, defaulting to `Y1`.
- [ ] 1.2 Bind the candle drawing composite and internal volume series to the selected axis pair.
- [ ] 1.3 Add validated `y_axis` selection to `PlotEconometricSeries`, defaulting to `Y1`.
- [ ] 1.4 Bind the econometric line, markers, and tooltip interaction container to the selected axis pair.
- [ ] 1.5 Reject conflicting `axes` entries in renderer extension kwargs.

## 2. DearCyFi Integration

- [ ] 2.1 Add a backward-compatible candle Y-axis argument to `DearCyFi.set_data(...)`.
- [ ] 2.2 Preserve or update the complete candle composite axis assignment when candle data is replaced.
- [ ] 2.3 Verify that collapse and restoration continue to change only X coordinates.

## 3. Demo and Documentation

- [ ] 3.1 Configure and label `Y3` as the demo's econometric scale while retaining candle prices on `Y1`.
- [ ] 3.2 Create the toy econometric series on `Y3` and independently fit candle and econometric axes after loading.
- [ ] 3.3 Document Y-axis selection, host-owned axis configuration, and the optional diagnostic `Y2` reservation.

## 4. Validation

- [ ] 4.1 Add focused tests for defaults, all supported Y axes, invalid axes, and complete composite propagation.
- [ ] 4.2 Add a regression test for changing the candle axis through a later `set_data(...)` call.
- [ ] 4.3 Run the focused candle, econometric, collapse-coordination, and demo-provider tests.
- [ ] 4.4 Run the full test suite and manually verify the demo before and after time collapse.
