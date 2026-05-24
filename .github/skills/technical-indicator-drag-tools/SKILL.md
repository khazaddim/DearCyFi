---
name: technical-indicator-drag-tools
description: "Use when: designing, reviewing, or implementing DearCyFi technical indicator drawing tools, draggable overlays, resizable rectangles, trend lines, Fibonacci tools, invisible-button hit regions, DearCyGui DrawInvisibleButton interaction, MouseCursorHandler behavior, or adaptations of dearcygui.utils.draw_draggable.py."
argument-hint: "DearCyFi TA overlay or draggable drawing task"
---

# Technical Indicator Drag Tools

## When To Use

Use this skill when work involves DearCyFi technical-analysis overlays or interactive drawing tools, especially:

- Draggable or resizable chart objects such as rectangles, ranges, channels, trend lines, handles, anchors, or Fibonacci-style tools.
- Choosing between plot-owned hit testing, axis locking, and `DrawInvisibleButton` capture.
- Studying or adapting `dearcygui.utils.draw_draggable.py`, including `DragPoint`, `DragHLine`, `DragVLine`, and `DragRect`.
- Adding cursor feedback with `MouseCursorHandler` for resize/move affordances.
- Moving proof-of-concept interaction code from `examples/TA/` into `src/dearcyfi/`.

## Source Pattern

The reference implementation lives in the installed DearCyGui package at `.venv/Lib/site-packages/dearcygui/utils/draw_draggable.py`.

Treat that file as a reference, not a project source file. Do not modify files under `.venv/` for DearCyFi features. Instead, copy the relevant ideas into project-owned modules under `src/dearcyfi/` or focused proof-of-concept examples under `examples/TA/`.

## Core Lesson

Pure plot-owned hit testing can detect hover and intent, but it does not own the mouse drag. In a plot, the same drag can still pan the plot unless another item captures the mouse or the axes are locked.

For draggable and resizable TA tools, prefer small semantic `DrawInvisibleButton` regions because they become the active DearCyGui item and block plot panning only where interaction is intended.

## Recommended Architecture

Build interactive TA tools as reusable classes with a clean public API, while using invisible buttons internally for input ownership.

Good shape:

- Visible items: `DrawRect`, `DrawLine`, `DrawText`, etc.
- Interactive items: `DrawInvisibleButton` for center, edge, corner, anchor, or segment handles.
- Shared handlers: use `HandlerList` and class methods for performance when many tools or handles may exist.
- Tool state: keep geometry, drag backup geometry, active handle type, hover count, and callbacks on the tool instance.
- Public callbacks: expose high-level `on_hover`, `on_dragging`, `on_dragged`, or subclass hooks rather than leaking every internal button.

## Interaction Zones

Use multiple small capture zones instead of one large blocker when possible.

For a rectangle-like tool:

- Center button: move the whole object, if moving is enabled.
- Edge buttons: resize one axis.
- Corner buttons: resize both axes.
- No button outside those zones: plot pan/zoom remains available.

For a line-like tool:

- Anchor buttons: move endpoints.
- Segment button: move the whole line, if enabled.
- Optional midpoint/extension handles: adjust special tool behavior.

## Cursor Feedback

`DrawRect` and other visible draw items do not change the cursor by themselves.

Cursor changes come from handlers attached to the invisible interaction items. The `DragRect` pattern uses a `ConditionalHandler` containing both a `MouseCursorHandler` and a `HoverHandler`. When the invisible button is hovered, the cursor handler applies the desired cursor.

Use cursor choices that match the action:

- Center/move: `dcg.MouseCursor.RESIZE_ALL`.
- Horizontal edge resize: `dcg.MouseCursor.RESIZE_NS` or the appropriate vertical sizing cursor depending on axis orientation.
- Vertical edge resize: `dcg.MouseCursor.RESIZE_EW`.
- Corners: `dcg.MouseCursor.RESIZE_NESW` or `dcg.MouseCursor.RESIZE_NWSE`.

## Drag Geometry Rules

Inside plot coordinates, `DrawInvisibleButton` drag deltas are returned in plot coordinates. Apply those deltas to backup geometry captured at drag start.

Recommended flow:

1. On first drag event, store backup geometry and active handle type.
2. During dragging, compute new geometry from backup geometry plus `drag_deltas`.
3. Normalize or clamp geometry so corners do not invert unexpectedly unless inversion is an intended behavior.
4. Update visible draw items and invisible button positions together.
5. Wake the viewport after geometry changes.
6. Release locks or reset active state on dragged/release.

## Performance Notes

DearCyGui handler objects can be shared across instances. The `draw_draggable.py` utilities use class-level weak references to shared `HandlerList` objects to reduce memory and object churn.

When implementing a production DearCyFi tool that may appear many times on one chart, consider this pattern:

- Store shared handlers at the class level.
- Use classmethod handlers.
- Resolve the tool instance from `target.parent` when the target is an internal `DrawInvisibleButton`.
- Keep per-instance geometry and callback state on `self`.

For a small proof of concept, per-instance handlers are acceptable if they keep the code easier to read.

## DearCyFi Implementation Guidance

When adapting this for `src/dearcyfi/`:

- Keep the tool API domain-focused: trend line, range box, Fibonacci retracement, support/resistance line, etc.
- Hide invisible button plumbing behind the tool class.
- Preserve plot interactions outside the tool's interaction zones.
- Prefer screen-space hit thickness via `min_side` or negative thickness where DearCyGui supports it, so handles remain usable at different zoom levels.
- Avoid depending on `.venv` paths or vendored source edits.
- Add focused examples under `examples/TA/` before hardening the API in `src/dearcyfi/`.

## Current PoC Context

The active experimentation area is `examples/TA/TA_PoC.py`.

Earlier plot-owned hit testing was useful for understanding hover and manual containment, but dragging and resizing competed with plot panning. The `draw_draggable.py` pattern is the stronger basis for production TA tools because it combines a class abstraction with invisible-button input capture and cursor feedback.