## 1. Implementation

- [ ] 1.1 Require the custom DearCyGui plot context-menu capability with a clear
  error for unsupported builds.
- [ ] 1.2 Add chart-owned collapse, vectorized-method, gap-report, source
  status, and diagnostics menu controls using the existing chart methods and
  properties.
- [ ] 1.3 Synchronize checkmarks and source status with chart state after menu
  and direct API actions, source changes, data replacement, and failed collapse.
- [ ] 1.4 Remove the moved demo sidebar controls while retaining unrelated
  bar-loading controls and existing programmatic APIs.
- [ ] 1.5 Document the menu, method-selection behavior, status callback, and
  custom DearCyGui requirement.

## 2. Validation

- [ ] 2.1 Add focused tests for both collapse methods, restoration, method
  changes while collapsed, diagnostics, synchronization, and failed collapse.
- [ ] 2.2 Run targeted tests with the installed custom DearCyGui wheel.
- [ ] 2.3 Verify the native plot menu retains its existing entries alongside
  the new item using a rendered probe or manual interaction.
