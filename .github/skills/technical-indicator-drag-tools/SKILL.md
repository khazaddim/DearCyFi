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

## File Structure Map

`draw_draggable.py` is organized as a family of `dcg.DrawingList` subclasses. Each class bundles visible drawing items, invisible interaction items, shared handlers, public properties, and optional clamping.

```text
draw_draggable.py
|-- DragPoint
|   |-- Visible: DrawCircle
|   |-- Interactive: one DrawInvisibleButton
|   |-- Motion: x/y point dragging
|   |-- Cursor: RESIZE_ALL
|
|-- DragHLine
|   |-- Visible: DrawLine with horizontal direction
|   |-- Interactive: one long horizontal DrawInvisibleButton
|   |-- Motion: vertical-only dragging
|   |-- Cursor: vertical resize style
|
|-- DragVLine
|   |-- Visible: DrawLine with vertical direction
|   |-- Interactive: one long vertical DrawInvisibleButton
|   |-- Motion: horizontal-only dragging
|   |-- Cursor: horizontal resize style
|
`-- DragRect
	|-- Visible: DrawRect plus optional diagonal DrawLine items
	|-- Interactive: nine DrawInvisibleButton items
	|-- Motion: center move, edge resize, corner resize
	|-- Cursor: move, edge resize, or corner resize depending on handle
	`-- Optional hints: DrawCircle children under selected buttons
```

The recurring pattern is:

```text
DrawingList tool
|-- visible drawing item(s)
|-- invisible button(s) for input ownership
|-- shared handler list(s)
|-- geometry state and backup geometry
|-- public properties that update visible and invisible geometry together
`-- public callbacks or hooks for tool users
```

## Object Hierarchy Diagrams

`DragPoint` is the simplest mental model. One visible item and one invisible input owner move together.

```text
DragPoint : dcg.DrawingList
|-- _invisible : dcg.DrawInvisibleButton
|   `-- handlers: shared HandlerList
|       |-- HoverHandler -> handler_hover
|       |-- DraggingHandler -> handler_dragging
|       |-- DraggedHandler -> handler_dragged
|       `-- ConditionalHandler
|           |-- MouseCursorHandler(RESIZE_ALL)
|           `-- HoverHandler
`-- _visible : dcg.DrawCircle
```

`DragRect` is the important rectangle model for TA overlays.

```text
DragRect : dcg.DrawingList
|-- _visible_rect : dcg.DrawRect
|-- _diagonal1    : dcg.DrawLine, hidden until hover
|-- _diagonal2    : dcg.DrawLine, hidden until hover
|
|-- _center_button : dcg.DrawInvisibleButton -> move
|-- _edge_top      : dcg.DrawInvisibleButton -> resize y1
|-- _edge_bottom   : dcg.DrawInvisibleButton -> resize y2
|-- _edge_left     : dcg.DrawInvisibleButton -> resize x1
|-- _edge_right    : dcg.DrawInvisibleButton -> resize x2
|-- _corner_tl     : dcg.DrawInvisibleButton -> resize x1/y1
|-- _corner_tr     : dcg.DrawInvisibleButton -> resize x2/y1
|-- _corner_bl     : dcg.DrawInvisibleButton -> resize x1/y2
`-- _corner_br     : dcg.DrawInvisibleButton -> resize x2/y2
```

Each button gets a matching shared `HandlerList`:

```text
HandlerList for one DragRect button
|-- HoverHandler        -> public on_hover callback
|-- GotHoverHandler     -> show diagonals/hints
|-- LostHoverHandler    -> hide diagonals/hints when hover_count reaches zero
|-- DraggingHandler     -> update geometry continuously
|-- DraggedHandler      -> finish drag state
`-- ConditionalHandler
	|-- MouseCursorHandler(cursor chosen for this button)
	`-- HoverHandler(condition for the cursor)
```

## Important Code Patterns

### 1. Visible and Invisible Items Are Created Together

The visible item draws the tool. The invisible item owns mouse interaction.

```python
class DragPoint(dcg.DrawingList):
	def __init__(self, context: dcg.Context, *args, **kwargs) -> None:
		with self:
			self._invisible = dcg.DrawInvisibleButton(context)
			self._visible = dcg.DrawCircle(context)

		self._handlers = DragPoint._get_handlers(context)
		self.setup_callbacks()
		super().__init__(context, *args, **kwargs)
```

For `DragRect`, this expands to one visible rectangle, optional diagonals, and nine invisible buttons.

```python
with self:
	self._visible_rect = dcg.DrawRect(context)
	self._diagonal1 = dcg.DrawLine(context, show=False)
	self._diagonal2 = dcg.DrawLine(context, show=False)

	self._center_button = dcg.DrawInvisibleButton(context)
	self._edge_top = dcg.DrawInvisibleButton(context)
	self._edge_bottom = dcg.DrawInvisibleButton(context)
	self._edge_left = dcg.DrawInvisibleButton(context)
	self._edge_right = dcg.DrawInvisibleButton(context)
	self._corner_tl = dcg.DrawInvisibleButton(context)
	self._corner_tr = dcg.DrawInvisibleButton(context)
	self._corner_bl = dcg.DrawInvisibleButton(context)
	self._corner_br = dcg.DrawInvisibleButton(context)
```

### 2. Shared Handlers Keep Many Tools Cheap

The classes keep a weak reference to shared handlers. If a handler still exists for the same context, reuse it.

```python
if cls.__handlers_ref is not None:
	handlers = cls.__handlers_ref()
	if handlers is not None and handlers.context == context:
		return handlers

handlers = dcg.HandlerList(context)
with handlers:
	dcg.HoverHandler(context, callback=cls.handler_hover)
	dcg.DraggingHandler(context, callback=cls.handler_dragging)
	dcg.DraggedHandler(context, callback=cls.handler_dragged)

cls.__handlers_ref = weakref.ref(handlers)
return handlers
```

For `DragRect`, there are nine shared handler lists, one per button role.

### 3. Cursor Feedback Is Handler-Driven

Visible draw items do not set cursors. Cursor changes come from `MouseCursorHandler` under a `ConditionalHandler` gated by hover.

```python
cursor_on_hover = dcg.ConditionalHandler(context)
with cursor_on_hover:
	if i == 0:
		cursor = dcg.MouseCursor.RESIZE_ALL
	elif i in (1, 2, 3, 4):
		cursor = dcg.MouseCursor.RESIZE_NS if i <= 2 else dcg.MouseCursor.RESIZE_EW
	else:
		cursor = dcg.MouseCursor.RESIZE_NESW if i in (5, 8) else dcg.MouseCursor.RESIZE_NWSE

	dcg.MouseCursorHandler(context, cursor=cursor)
	dcg.HoverHandler(context)
```

### 4. Geometry Updates Must Move Both the Drawing and Buttons

The visible rectangle and every invisible input region must stay synchronized.

```python
self._visible_rect.pmin = self._rect.p1
self._visible_rect.pmax = self._rect.p2

self._corner_tl.p1 = self._rect.p1
self._corner_tl.p2 = self._rect.p1
self._corner_tl.min_side = self._grab_thickness

self._edge_top.p1 = self._rect.p1
self._edge_top.p2 = (self._rect.x2, self._rect.y1)
self._edge_top.min_side = self._grab_thickness

self._center_button.p1 = 0.75 * self._rect.center + 0.25 * self._rect.p1
self._center_button.p2 = 0.75 * self._rect.center + 0.25 * self._rect.p2
self._center_button.min_side = self._grab_thickness
```

### 5. Dragging Uses Backup Geometry Plus Plot-Coordinate Deltas

Inside plots, `DrawInvisibleButton` drag deltas are already in plot coordinates. Store backup geometry on the first drag callback, then compute new geometry from backup plus delta.

```python
if not self._was_dragging or self._drag_type != drag_type:
	self._backup_rect = dcg.Rect(self._rect.x1, self._rect.y1, self._rect.x2, self._rect.y2)
	self._was_dragging = True
	self._drag_type = drag_type

dx, dy = drag_deltas[0], drag_deltas[1]

if self._drag_type == "move":
	new_rect.x1 = self._backup_rect.x1 + dx
	new_rect.y1 = self._backup_rect.y1 + dy
	new_rect.x2 = self._backup_rect.x2 + dx
	new_rect.y2 = self._backup_rect.y2 + dy
elif self._drag_type == "corner_tr":
	new_rect.x2 = self._backup_rect.x2 + dx
	new_rect.y1 = self._backup_rect.y1 + dy
elif self._drag_type == "edge_left":
	new_rect.x1 = self._backup_rect.x1 + dx
```

### 6. Public State Is Redirected to Internal Buttons

The tool behaves like one object, but input state lives on the internal invisible button(s). The class redirects state, input, capture, and user handlers.

```python
@property
def state(self) -> dcg.ItemStateView:
	return self._center_button.state

@property
def capture_mouse(self) -> bool:
	return self._center_button.capture_mouse

@capture_mouse.setter
def capture_mouse(self, value: bool) -> None:
	buttons = [
		self._center_button,
		self._edge_top, self._edge_bottom, self._edge_left, self._edge_right,
		self._corner_tl, self._corner_tr, self._corner_bl, self._corner_br,
	]
	for button in buttons:
		button.capture_mouse = value
```

## Interaction Lifecycle

Use this lifecycle as the mental model for draggable DearCyGui drawing tools:

```text
construct tool
-> create visible drawing children
-> create invisible button children
-> create or reuse shared handlers
-> attach handlers to invisible buttons
-> initialize geometry for visible items and hit regions
-> hover updates cursor and visual hints
-> first dragging callback stores backup geometry and active handle type
-> dragging callback computes geometry from backup + drag delta
-> geometry update moves visible items and invisible buttons together
-> viewport wakes so the redraw is visible
-> dragged/release callback clears active state and calls public callback
```

Important detail: there is no separate explicit `on_drag_start` handler in the reference utilities. The first `DraggingHandler` call acts as drag start by checking `_was_dragging` and storing backup geometry.

```python
if not self._was_dragging or self._drag_type != drag_type:
	self._backup_rect = dcg.Rect(self._rect.x1, self._rect.y1, self._rect.x2, self._rect.y2)
	self._was_dragging = True
	self._drag_type = drag_type
```

That pattern matters for DearCyFi tools because `drag_deltas` are cumulative from activation. Always combine deltas with backup geometry, not with the geometry from the previous frame.

## Gotchas Learned From The PoC

These are the traps that came up while comparing plot-owned hit testing with invisible-button interaction.

### Plot-Owned Hit Testing Does Not Capture Drags

Plot handlers can manually inspect `plot.X1.mouse_coord` and `plot.Y1.mouse_coord`, so they are useful for passive diagnostics and hover readouts. They do not become the active DearCyGui item, so the plot can still interpret the same drag as pan.

Use plot-owned handlers for non-capturing tools. Use `DrawInvisibleButton` for dragging or resizing.

### Axis Locking Is A Workaround, Not The Preferred Tool Interaction

Temporarily locking plot axes can stop panning while a tool drag is active, but it adds state coordination and can feel coarse. Invisible buttons solve the root interaction ownership problem by making only the intended handle active.

### `capture_mouse` Is Not The Same As Hit-Test Ownership

`capture_mouse=True` helps an invisible button retain the drag after it becomes active. It does not make a normal visible draw item interactive, and it does not make plot-owned hit testing consume the drag.

The item still needs to win the initial hover/activation test. In this pattern, that item is a `DrawInvisibleButton`.

### Visible Drawing Items Are Not Interactive

`DrawRect`, `DrawLine`, `DrawCircle`, and similar drawing items are visual. They do not maintain hover/click/drag state. Attach handlers to `DrawInvisibleButton` items, not to the visible draw item, unless DearCyGui explicitly documents otherwise for that item.

### Button Order Matters When Hit Regions Overlap

`DrawInvisibleButton` can overlap other invisible buttons. DearCyGui gives hover to the last hovered item in the rendering tree, and an active button retains hover while its activation button is pressed.

For rectangles, create broad regions first and more specific regions later. The `DragRect` pattern creates center and edge buttons before corner buttons so corner handles can win priority.

### Always Update Visible Geometry And Hit Geometry Together

If the visible rectangle moves but the invisible buttons do not, the tool looks correct but clicks happen in stale locations. If invisible buttons move but visible geometry does not, interaction feels detached from the drawing.

Put all geometry synchronization in one method such as `_update_rect_geometry()` or `_update_draw_items()` and call it after every property or drag mutation.

### Use Screen-Space Hit Thickness For Handles

Handles should remain usable while zooming. The DearCyGui pattern uses `min_side` on `DrawInvisibleButton` and negative visual sizes/thicknesses where supported so the interaction target stays a practical screen size.

### Drag Deltas Inside Plots Are Plot-Coordinate Deltas

When a `DrawInvisibleButton` is inside a plot, `DraggingHandler` receives deltas in plot/data coordinates. Do not treat those deltas as pixels when updating TA tool geometry.

### Callback State Should Be Read Under The Mutex, But Called After Release

The reference utilities read callback fields while holding `self.mutex`, then release the mutex before invoking the callback. This avoids calling user code while holding internal locks.

### Do Not Edit The Vendored DearCyGui Utility

`draw_draggable.py` under `.venv/` is reference material. DearCyFi adaptations belong in `src/dearcyfi/` or proof-of-concept examples under `examples/TA/`.

## Project Reference Example

The current best local rectangle example is `examples/TA/TA_PoC_Invis_Btns.py`.

Use it as a DearCyFi-owned reference for a small interactive tool class built from visible drawing items plus internal invisible hit regions.

What this example demonstrates:

- A reusable `MovableResizableBoxIndicator` class instead of plot-owned hit testing.
- One center `DrawInvisibleButton` for move ownership.
- Four corner `DrawInvisibleButton` items for resize ownership.
- Visible corner handle rectangles that stay a fixed visual size for that indicator instance.
- Screen-space handle hit targets via `min_side`, separate from the visible handle rectangles.
- Cursor routing with `ConditionalHandler` and `MouseCursorHandler`.
- Backup geometry captured on first drag, then geometry recomputed from cumulative drag deltas.
- Geometry synchronization in one `update_draw_items()` method.
- Normalized draw bounds for display, while still allowing raw corner coordinates to cross when inversion is enabled.
- An `allow_inversion` kwarg so the same class can support either clamped or invertible rectangle behavior.

Important distinction:

- `draw_draggable.py` is the generic upstream pattern reference.
- `examples/TA/TA_PoC_Invis_Btns.py` is the project-specific rectangle PoC showing how that pattern maps into DearCyFi technical-indicator work.

When adapting this example into production code, keep the interaction architecture but move the class into project-owned source under `src/dearcyfi/`, tighten the public API, and replace PoC status-text updates with real callbacks or application hooks.

## Adaptation Recipe For DearCyFi Tools

When building a new technical indicator drawing tool from this pattern:

1. Name the domain object first, such as `TrendLineTool`, `RangeBoxTool`, or `FibonacciRetracementTool`.
2. Choose the visible drawing items that represent the tool.
3. Choose semantic interaction zones: anchors, segment, center, edges, corners, or level handles.
4. Create `DrawInvisibleButton` items for those zones.
5. Assign a handle type to each button, such as `anchor_left`, `anchor_right`, `move`, `edge_top`, or `corner_br`.
6. Map each handle type to the correct cursor.
7. On first drag, store backup geometry and active handle type.
8. During drag, compute new geometry from backup geometry plus plot-coordinate deltas.
9. Normalize, clamp, or constrain geometry as the tool requires.
10. Update visible draw items and invisible buttons in one geometry method.
11. Expose high-level hooks or callbacks for application code.
12. Keep plot panning available outside the invisible-button zones.

## Decision Guide

```text
Need passive mouse readout or diagnostics?
-> Plot-owned handlers are fine.

Need hover-only highlighting without drag ownership?
-> Plot-owned handlers can work, but invisible buttons give better cursor support.

Need dragging, resizing, or anchors?
-> Use DrawInvisibleButton interaction zones.

Need many tools or many handles?
-> Use shared HandlerList objects and classmethod handlers.

Need to keep handles usable across zoom levels?
-> Use min_side and screen-space visual sizing where possible.

Need plot pan/zoom to remain available?
-> Keep invisible buttons small and semantic instead of covering the whole plot or whole shape.
```

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