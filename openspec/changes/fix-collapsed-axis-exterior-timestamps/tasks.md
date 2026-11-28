## 1. Axis labeling

- [x] 1.1 Add an axis-specific inverse for exterior coordinates, preserving existing conversion at endpoints and retained bridges.
- [x] 1.2 Use it for regular and supplemental context labels, without adding tick markers or extra ticks. Use the current map on refresh.

## 2. Validation and documentation

- [x] 2.1 Test increasing exterior timestamps on both sides, follower round trips with a nonzero final shift, and unchanged endpoint and bridge conversions.
- [x] 2.2 Verify label strings and coordinates from both formatting paths: correct dates at and between follower ticks, configured date/time formats without markers, and no new ticks.
- [x] 2.3 Test a source append that changes the boundary and reveals a gap, and confirm map and follower refresh together. Check existing cursor-tag and observation-tooltip tests for regressions.
- [x] 2.4 Document the formulas and calendar limits in the README. Verify that exterior weekly observation coordinates resolve to their tooltip source dates.
- [x] 2.5 Verify that the cursor tag uses the axis timestamp before and after the source range, displays dates without an exterior marker, and preserves custom formatter text and drawing-tool conversion.
