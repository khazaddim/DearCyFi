## ADDED Requirements

### Requirement: Chart context-menu collapse toggle

DearCyFi SHALL add a checkable collapse toggle and method-selection checkbox to
the native DearCyGui plot context menu without replacing existing menu entries.

#### Scenario: Enable collapsed time
- **WHEN** the user checks the collapse item
- **THEN** the chart invokes the collapse operation selected by the method checkbox
- **AND** the checkmark reflects whether collapse actually succeeded

#### Scenario: Choose collapse method
- **WHEN** a chart is first created
- **THEN** vectorized collapse is selected by default
- **WHEN** the vectorized checkbox is unchecked before collapse
- **THEN** the scalar collapse method is used instead

#### Scenario: Change method while collapsed
- **WHEN** the vectorized checkbox changes while time is collapsed
- **THEN** the existing collapse remains unchanged
- **AND** the newly selected method applies to the next collapse

#### Scenario: Restore time
- **WHEN** the user unchecks the collapse item on a collapsed chart
- **THEN** the chart restores its original time coordinates
- **AND** the item is unchecked

#### Scenario: Chart state changes elsewhere
- **WHEN** direct API calls or chart lifecycle events collapse or restore
  the chart
- **THEN** the item reflects the actual collapse state when displayed

#### Scenario: Collapse has no selected source
- **WHEN** the user checks the item without a collapse source
- **THEN** the chart reports the existing source-selection status
- **AND** the item remains unchecked

### Requirement: Chart context-menu gap and diagnostic controls

DearCyFi SHALL provide access to gap reporting, the selected collapse source,
and existing date-label and diagnostic settings through its native plot menu.

#### Scenario: Inspect source gaps
- **WHEN** the user selects `Gaps n' Chunks`
- **THEN** the chart invokes its existing gap-report action for the selected source
- **AND** reports its status through the existing status callback

#### Scenario: Show the selected source
- **WHEN** the context menu is displayed
- **THEN** it identifies the current collapse source or indicates none is selected

#### Scenario: Change diagnostic settings
- **WHEN** the user opens the `Diagnostics` submenu
- **THEN** it offers checkboxes for `Date Context Labels`, `Date Context Diagnostic`,
  and `Label Overlap Diagnostic`
- **AND** those checkboxes reflect and update the corresponding chart properties

#### Scenario: Require context-menu support
- **WHEN** DearCyFi is constructed with a DearCyGui build lacking plot context-menu support
- **THEN** construction fails with a clear compatibility error

### Requirement: Demo gap controls reside in the chart menu

The demo SHALL remove its sidebar gap and diagnostic controls in favor of the
chart's context menu, move bar-loading controls to `Fake Candle Controls`, and
remove the empty `Collapsing Controls` section.

#### Scenario: Access gap controls in the demo
- **WHEN** the demo is running with the required custom DearCyGui build
- **THEN** users access collapse, method selection, source status, gap reporting,
  and date-label diagnostics through the chart's context menu
- **AND** the demo sidebar no longer duplicates those controls
- **AND** the `Collapsing Controls` section is no longer present

#### Scenario: Load bar data in the demo
- **WHEN** the user opens `Fake Candle Controls`
- **THEN** the existing `Load Bar Data` button and `Bar Length Mode` selector
  are available there
- **AND** bar loading continues to use the selected mode
