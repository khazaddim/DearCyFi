## 1. Design and Approval

- [ ] 1.1 Specify collapsed interval and approximate-week conversions, average-history initialization of the uncollapsed shift, and behavior on insufficient history or source replacement.
- [ ] 1.2 Compare historical compressed-time uncertainty estimators on deterministic daily and minute examples; document the selected estimator, units, minimum data and limitations.
- [ ] 1.3 Define future axis/cursor presentation, the shift controls, source-series behavior, and error-bar configuration.
- [ ] 1.4 Review the resolved proposal and obtain approval before implementation.

## 2. Implementation

- [ ] 2.1 Add independently configurable collapsed and uncollapsed econometric display shifts without mutating source timestamps or values.
- [ ] 2.2 Integrate shifts with projection, collapse/restore, source lifecycle, incremental streaming, and failure recovery without double application.
- [ ] 2.3 Implement the approved historical-compression uncertainty estimate and horizontal ranges on eligible future observations.
- [ ] 2.4 Make future axis, cursor and tooltip presentation explicitly approximate or unavailable when an exact date cannot be established.
- [ ] 2.5 Add demo controls and document units, initial conversion, limitations, and the distinction between source dates and displayed positions.

## 3. Verification

- [ ] 3.1 Test positive, negative and zero shifts at weekly, daily and minute cadences, including independent mode settings and both input units.
- [ ] 3.2 Test collapse/restore, source replacement, streaming append/update, follower reprojection, and failure handling.
- [ ] 3.3 Test historical-gap uncertainty estimates, future error-bar rendering, legend visibility, and insufficient-history behavior.
- [ ] 3.4 Test future axis/cursor and source-date tooltip behavior, including the boundary at the final candle.
- [ ] 3.5 Run the demo walkthrough, relevant automated tests, and `openspec validate add-econometric-series-display-shift --strict --no-interactive`.
