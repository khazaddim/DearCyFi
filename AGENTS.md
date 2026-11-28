<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

# DearCyFi Agent Notes

When working on interactive DearCyFi technical indicator tools, draggable chart overlays, resize handles, or DearCyGui `DrawInvisibleButton` interaction patterns, use the project skill at `.github/skills/technical-indicator-drag-tools/SKILL.md`.

Use that skill before adapting behavior from `dearcygui.utils.draw_draggable.py` into `src/dearcyfi/` or `examples/TA/`. Treat files under `.venv/` as reference material only; do not edit vendored package files for DearCyFi features.

When designing, implementing, reviewing, or testing DearCyFi demo widgets that browse or load data from Parquet, DuckDB, databases, brokers, Tastytrade/Tastyworks, APIs, or sibling repositories, use `.github/skills/data-source-widgets/SKILL.md`.

Use that skill before adapting `examples/DearCyFi_Demo/toy_data_browser.py` into a provider widget or adding options, liquidity, or other non-candle loaders. DearCyFi does not yet provide gap-aware econometric series plotting; preserve non-candle timestamps and gaps at the adapter boundary, and do not implement that missing series capability incidentally during widget work.

When designing, implementing, reviewing, or testing a new or changed DearCyFi plot series (econometric, options, overlay, or other composite series built from DearCyGui drawing primitives), or fixing a series' legend toggle, tooltip, axis fit, Y-axis, or time-collapse behavior, use `.github/skills/custom-plot-series/SKILL.md`. Use `src/dearcyfi/econometric_series.py` as the reference implementation.

When adding or changing chart snapshot kinds, the v1 codec, or transactional capture and restore, use the [chart persistence skill](.github/skills/chart-persistence/SKILL.md).