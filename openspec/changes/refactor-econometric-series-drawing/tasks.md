## 1. Validate Drawing Capabilities

- [x] 1.1 Verify the custom DearCyGui build's `DrawInPlot` legend visibility, child interaction suppression, active-tooltip lifetime, and visibility persistence across updates using an actual rendered plot.
- [x] 1.2 Verify screen-space primitive size and line thickness through zoom and pan, and fitting for finite observations, isolated points, hidden series, and empty or non-finite data on X1 and the selected Y axis.
- [x] 1.3 Determine and document a fitting and tooltip-lifetime implementation if native drawing behavior is insufficient; revise the proposal and seek approval if the single-item contract is not feasible.

## 2. Implementation

- [x] 2.1 Inventory existing native options and direct object usage; document supported styling and migration.
- [x] 2.2 Implement one labeled, axis-aware `DrawInPlot` containing line segments, optional circular markers, and optional tooltip targets.
- [x] 2.3 Draw only finite observations, break segments at invalid observations, use screen-space marker sizing, and implement correct fit behavior independently of markers and tooltips.
- [x] 2.4 Preserve validated updates, source and plot dates, collapse restoration, selected Y axis, legend visibility, and safe tooltip cleanup.
- [x] 2.5 Replace native-specific extension kwargs and native object attributes with the explicitly documented supported styling interface; reject legacy options clearly.

## 3. Regression Coverage

- [x] 3.1 Add focused tests for finite segments, NaN breaks, isolated points, marker and tooltip options, validation failures, updates, and stale hit-region removal.
- [x] 3.2 Test source-date tooltips, collapse and restore, all supported Y axes, and multiple independent series, including updates while hidden.
- [x] 3.3 Test fit bounds, empty and non-finite data, marker sizing, unsupported legacy options, and any nontrivial tooltip cleanup logic at the appropriate integration level.
- [ ] 3.4 Run an actual GUI regression: toggle the legend off and on, including while a tooltip is open; verify line, dots, and hover targets all follow the toggle, and fit, zoom, pan, and time collapse remain correct.
- [x] 3.5 Run the smallest relevant econometric, axis-assignment, collapse-coordination, and demo-widget test selection; report any environment limitations.

## 4. Documentation and OpenSpec

- [x] 4.1 Document the public styling options, units, defaults, limitations, and migration from native attributes and kwargs in the README and class API.
- [x] 4.2 Validate this change with `openspec validate refactor-econometric-series-drawing --strict`.
- [ ] 4.3 Before archiving this change, archive `add-econometric-series-collapse-source` and ensure its econometric requirements are present; preserve the separately proposed axis-assignment requirements.
