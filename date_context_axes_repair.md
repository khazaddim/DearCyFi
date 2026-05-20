# Date Context Axes Repair

This note explains the custom x-axis label repair pass added to `DearCyFi` to replace the older boundary tick injection behavior.

## Problem

The time locator can produce technically valid labels that are hard to read after time collapse. A common case happens around hourly candles:

```text
9/27/24       9/30          10/3          10/8
12am  3am  6am  2am  5am   12am  3am     2am
```

The lower row contains plenty of time labels, but the upper row can have date labels that are several days apart. This leaves long stretches where the user sees times without enough date context.

The old approach tried to solve this by injecting additional boundary ticks at calendar boundaries. That helped some sparse-label cases, but it also created a second spacing system independent of the locator. Those extra tick positions could collide with labels that the locator had already decided were safe.

## New Approach

The new feature is a post-processing pass called **date context label repair**.

Instead of creating new ticks, it repairs labels that already exist. It waits until the locator has generated ticks and `DearCyFi` has grouped them by x-position, then it looks for long screen-space gaps between labels that already have upper-row date context.

When it finds a gap that is too large, it chooses an existing lower-row label inside that gap and promotes it by adding a date context line above it.

For example, an existing label like this:

```text
3am
```

can become:

```text
10/2
3am
```

The key design point is that the x-position already existed. The repair pass enriches that label instead of adding another label candidate to the axis.

## Execution Flow

The repair runs inside `DearCyFi.axes_resize_callback(...)`.

1. The time locator generates ticks for the current visible x-range.
2. If time is collapsed, `DearCyFi` expands each collapsed x-position back to real time and reformats the tick labels.
3. Visible ticks are grouped by rounded x-position into `by_pos` entries:

```python
{
    "pos": float,
    "major": upper_row_label_or_None,
    "minor": lower_row_label_or_None,
}
```

4. If `apply_date_context_labels` is enabled, `_apply_date_context_label_repair(...)` mutates selected `by_pos` entries by filling their `major` label slot.
5. The final x-label strings are assembled from `by_pos`:

```text
major
minor
```

6. `_apply_custom_x_labels(...)` sends the repaired label list to the plot axis.
7. If `date_context_debug` is enabled, the diagnostic `PlotDigital` series marks the x-positions that were repaired.

## Label Selection Rules

The repair pass is intentionally conservative.

It only considers existing labels that have a lower-row label and no upper-row label:

```python
entry.get("major") is None and entry.get("minor") is not None
```

That means it does not add a new tick and does not overwrite existing upper-row date labels.

It builds anchors from:

- the visible x-range minimum
- existing upper-row label positions
- the visible x-range maximum

Then it scans each anchor-to-anchor gap. If a gap is wider than `date_context_max_gap_px`, converted into axis units using `scaling_factor`, it chooses one or more existing labels inside the gap to repair.

The chosen repair positions must also stay at least `date_context_min_spacing_px` away from other repaired positions and existing upper-row labels.

## Formatting Rules

The date context label format depends on the current `unit0` locator scale:

| `unit0` scale | Added context |
| --- | --- |
| hour or finer | day/month, for example `10/2` |
| day | month/year, for example `Oct 2024` |
| month | year, for example `2024` |
| year | no repair |

When the x-axis is collapsed, the repair pass expands the collapsed x-position back into real time before formatting the context label. This keeps repaired labels aligned with the original calendar time rather than the compressed chart coordinate.

## Public Controls

### `apply_date_context_labels`

This is the new main feature flag.

```python
plot.apply_date_context_labels = True
```

When set, it triggers `X1.fit()` so the custom labels are recomputed immediately.

### `date_context_debug`

This toggles the diagnostic `PlotDigital` overlay.

```python
plot.date_context_debug = True
```

The diagnostic uses the existing hidden Y2 diagnostic axis and draws amber pulses at repaired label positions.

### Compatibility Aliases

The old property names still exist so older call sites do not fail immediately:

```python
plot.inject_boundary_ticks = True   # forwards to apply_date_context_labels
plot.boundary_tick_debug = True     # forwards to date_context_debug
```

The constructor also accepts the new keyword:

```python
DearCyFi(..., apply_date_context_labels=False)
```

The old `inject_boundary_ticks` constructor keyword is still accepted as a compatibility override.

## Demo Changes

The demo controls were renamed to describe the new behavior:

- `Date Context Labels` toggles `plot.apply_date_context_labels`
- `Date Context Diagnostic` toggles `plot.date_context_debug`

The demo initializes `DearCyFi` with `apply_date_context_labels=False` so the checkbox state and plot state match on startup.

## Diagnostic Text

The floating debug text now reports repaired labels with:

```text
date_context_labels=N
```

This replaces the older boundary tick count display.

## Rationale

### Why replace boundary tick injection?

Boundary injection added new x-label positions based on calendar boundaries. Those positions did not come from the locator's normal density decisions, so they could collide with labels that were already present.

The new repair pass works only with positions that already survived the locator and grouping pipeline. This makes it less likely to create new overlap problems.

### Why not tune `minor_per_major` dynamically?

Changing the locator density can be useful, but it is a blunt tool for this specific problem. At hourly scales, `minor_per_major` mainly controls how many lower-row hour labels appear inside each day. It does not directly guarantee better upper-row date context.

Reducing lower-row density might create more visual breathing room, but it would also remove useful intraday labels. Increasing density can make collisions worse. The repair pass targets the missing information directly: it adds date context only where the user has gone too long without it.

### Why add context above existing labels?

The axis renderer already supports a two-line label shape:

```text
upper date context
lower time context
```

Using that shape preserves the existing label coordinate and keeps the locator's spacing decisions mostly intact.

### Why use screen-space thresholds?

The user's problem is visual, not purely temporal. A five-day date gap may be fine when zoomed out but confusing when it spans a large portion of the viewport. The repair pass therefore uses pixel thresholds converted through `scaling_factor` so the behavior responds to zoom and viewport width.

## Tunable Values

Two instance attributes control the current behavior:

```python
plot.date_context_max_gap_px = 280.0
plot.date_context_min_spacing_px = 160.0
```

- `date_context_max_gap_px`: maximum desired screen-space gap between date-context labels before repair is attempted.
- `date_context_min_spacing_px`: minimum screen-space distance from existing upper-row context and other repaired labels.

Lowering `date_context_max_gap_px` adds context more often. Raising it makes the repair less active.

Lowering `date_context_min_spacing_px` allows repaired labels closer together. Raising it makes the repair more conservative.

## Current Limitations

- The repair pass estimates label spacing from x-position distance and `scaling_factor`; it does not run a full text-layout solver.
- It only repairs existing visible lower-row labels. If the locator produces no suitable lower-row labels inside a sparse gap, the pass leaves that gap alone.
- The diagnostic marks repaired positions, not the full computed text extents. Use the label-overlap diagnostic alongside it when checking collisions.

## Mental Model

The old feature asked:

> Where are the calendar boundaries, and should we inject ticks there?

The new feature asks:

> The labels that already exist are mostly good; where do they need extra date context so the user can stay oriented?
