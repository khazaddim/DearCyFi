## 1. Axis labeling

- [ ] 1.1 Add an axis-specific inverse for exterior coordinates, preserving existing conversion at endpoints and retained bridges.
- [ ] 1.2 Use it for regular and supplemental context labels. Qualify extrapolated ticks, recognize coincident unshifted follower observations without extra ticks, and use current projection state on refresh.

## 2. Validation and documentation

- [ ] 2.1 Test increasing exterior timestamps on both sides, follower round trips with a nonzero final shift, and unchanged endpoint and bridge conversions.
- [ ] 2.2 Verify the rendered label strings and coordinates from both formatting paths: exact dates at coincident follower ticks, marked extrapolations elsewhere, configured date/time formats, and no new ticks or marker leakage on restore.
- [ ] 2.3 Test a source append that changes the boundary and reveals a gap, and confirm map and follower refresh together. Check existing cursor-tag and observation-tooltip tests for regressions.
- [ ] 2.4 Document the formulas, marker, and calendar limits in the README. In the demo, pan and zoom past both candle boundaries with a weekly econometric follower, compare its dates with the axis and its tooltips, and repeat in original-time mode.
