# Project Context

## Purpose
DearCyFi is a financial charting toolkit built on DearCyGui, focused on plotting OHLC candlestick data and handling irregular time gaps (weekends, holidays, overnight sessions) on interactive time axes.

Primary goals:
- Provide a reusable `DearCyFi` plot component for host applications.
- Support optional time-gap collapsing while keeping readable, accurate time labels.
- Keep plotting utilities composable (candles, horizontal bars, time-locator helpers).

## Tech Stack
- Python 3.10+
- DearCyGui (`dearcygui`) for UI and plotting
- NumPy for numeric arrays and transformations
- Pandas for gap/chunk helper logic
- Pillow (optional) for text-width measurement in time tick locators
- Jupyter notebooks for exploration and prototyping

## Project Conventions

### Code Style
- Follow PEP 8 with type hints throughout (`|` unions and built-in generics are used).
- Prefer explicit, readable code over heavy abstraction.
- Use docstrings for public classes/functions and non-trivial behavior.
- Keep module-level utilities focused on a single domain (candles, bars, gap logic, time locator).
- Maintain backward-compatible behavior unless a change is explicitly marked breaking.

### Architecture Patterns
- Main reusable widget: `DearCyFi` class in `DearCyFi.py`.
- Plotting helpers are separated into utility modules:
	- `DCG_Candle_Utils.py` for candlesticks
	- `DCG_Bar_Utils.py` for horizontal bars
	- `candle_utils/gap_utils.py` for gap detection/collapse mapping
	- `PyTimeLocator/locator_time3.py` for time tick generation/formatting
- Demo wiring and manual interaction checks live in `DearCyFi_Demo.py`.
- Time-collapsing behavior is encapsulated by `GapCollapseManager` and consumed by `DearCyFi`.

### Testing Strategy
- Current testing is primarily manual/integration-oriented via `DearCyFi_Demo.py`.
- Notebook-based exploratory validation is used for time locator and synthetic data generation logic.
- For non-trivial logic changes, validate behavior with deterministic sample arrays and inspect edge cases:
	- empty/NaN inputs
	- weekend/holiday gaps
	- early/late range boundaries and label formatting
- When adding new capabilities, include at least one reproducible validation path (scripted check or demo scenario).

### Git Workflow
- Use short-lived feature branches for substantive changes.
- Keep commits focused and descriptive by intent (feature, fix, refactor, docs).
- Avoid bundling unrelated refactors with behavior changes.
- For OpenSpec-driven work, proposal/spec updates should be separated logically from implementation when practical.

## Domain Context
- Domain is market/financial charting.
- Time series may contain non-trading gaps (weekends, holidays, off-hours), and chart UX should optionally collapse those intervals.
- Correct and readable axis labeling is a core product concern, including major/minor tick layering and date/time formatting options.
- Candlestick and volume rendering must stay visually interpretable under zoom/pan and after time-collapse transforms.

## Important Constraints
- Must remain responsive in interactive GUI usage; avoid expensive per-frame work when possible.
- Preserve compatibility with existing demo flows and public class usage in `DearCyFi.py`.
- Keep dependencies minimal and justified.
- Be careful with timezone/local-time behavior, since labeling correctness is user-visible.
- Repository currently includes local/private helpers (for example `fmp_client_local.py`) that should not be treated as distributable package APIs.

## External Dependencies
- Python packages listed in `requirements.txt`: `requests`, `numpy`, `dearcygui`, `pillow`, plus currently listed `pytx`.
- The codebase also uses `pandas` and `pytz` in utility modules; dependency metadata should stay aligned with actual imports.
- Optional font metrics integration uses Pillow + DearCyGui font files for more accurate tick label width estimation.
