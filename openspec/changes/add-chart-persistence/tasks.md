## 1. Document and codec

- [ ] 1.1 Define the v1 envelope and typed records, data/display allowlists, stable ID/reference rules, timestamp and missing-value conventions, and empty-chart semantics.
- [ ] 1.2 Implement detached snapshot capture and validation, explicit kind dispatch, strict UTF-8 JSON with duplicate/non-finite rejection and size bounds, and actionable field/item errors.
- [ ] 1.3 Add programmatic path operations with bounded reads, same-directory temporary writes, explicit overwrite policy, atomic publication, and cleanup.

## 2. Chart state integration

- [ ] 2.1 Capture and reconstruct candle OHLCV/index, registered econometric series, and chart-owned horizontal bars from retained source data and supported presentation.
- [ ] 2.2 Capture SMA definitions and integrate explicit ID restoration and recomputation with the indicator manager. Map range boxes by kind to canonical source geometry and options; restore through the existing interactive tool lifecycle.
- [ ] 2.3 Capture and reconstruct the active collapse gap definitions and source/method settings, including a map extended by streaming. Reapply follower projection, drawing projection, calendar and context menu state.
- [ ] 2.4 Preserve axis enablement, labels, supported scales, initialized ranges, item `show` and native legend `enabled`, and other supported display state. Apply saved limits after projection and initial fit.
- [ ] 2.5 Stage and commit restore in place with rollback on preparation or publication failure. Replace all supported chart contents coherently, retain host-owned children, and dispose obsolete managed widgets, tooltip state, and registrations after commit.

## 3. UI, demo, and documentation

- [ ] 3.1 Add Save Chart and Open Chart to the existing plot menu with path entry, overwrite/replacement confirmation, cancel/retry, single-submission guards, and actionable status feedback. Keep file operations off render callbacks.
- [ ] 3.2 Integrate the demo's stream and provider reload boundaries, rebind restored series and indicator menus, handle stale popups, and leave the comparison plot untouched.
- [ ] 3.3 Document the menu and programmatic workflows, v1 fields and supported types/options, file limit, extension/version policy, host ownership boundaries, and privacy/sharing implications.
- [ ] 3.4 Create `.github/skills/chart-persistence/SKILL.md` and link it from the repository agent notes and the existing plot-series and drag-tool skills. Use the implemented SMA and range-box handlers as examples. Give contributors a checklist for stable kind tokens and IDs, type-specific parameters or canonical source-time geometry, dependency and display fields, explicit handler registration, validation, and restoration through the existing managers. Explain when a schema version change or migration is needed, how older readers handle unknown kinds, and which round-trip, collapse, and invalid-record tests to add for each new type.

## 4. Verification

- [ ] 4.1 Round trip a mixed chart without the demo/provider: gapped candles with volume and explicit index, econometric missing values, multiple editable SMAs, interactive range boxes, and horizontal bars. Also cover empty replacement and generated IDs after restore.
- [ ] 4.2 Compare saved and restored view, source/plot timestamps, follower gap policy, alternate collapse source, and drawing anchors, including a streamed map and an X1 limit inside a retained gap. Test standard time, enabled/disabled secondary axes, and native legend hide/show using a rendered probe.
- [ ] 4.3 Test malformed, unsupported, oversized, and inconsistent documents, including a sparse file or bounded stream at the size limit, duplicate IDs and JSON keys, null samples, non-finite numbers, and unsupported owned items. Verify no partial restore or incomplete save.
- [ ] 4.4 Inject failures in file writing/replacement and in chart projection/publication. Verify file preservation and cleanup, original view and objects, and demo stream behavior on failure, cancel, and success.
- [ ] 4.5 Exercise Save/Open, overwrite/replacement confirmation, cancel, and retry through the right-click popup; verify existing context and legend controls and that the comparison plot is unaffected.
- [ ] 4.6 Run targeted persistence, candle indicator, econometric, range box, axes, collapse, streaming, and demo tests with the supported custom DearCyGui build and document a manual walkthrough.
