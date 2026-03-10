## Context
DearCyFi currently behaves like a script-style repository with top-level modules imported directly from repository root. This works for local execution but is fragile for `pip` installs, where modules should resolve through an installable package namespace.

## Goals / Non-Goals
- Goals: Provide a pip-installable package, define one canonical import path, and make runtime dependencies accurate.
- Goals: Keep integration friction low for existing users.
- Non-Goals: Large-scale feature rewrites unrelated to packaging.
- Non-Goals: Re-architecting plotting behavior or time-axis algorithms.

## Decisions
- Decision: Use a package namespace with canonical public import `from dearcyfi import DearCyFi`.
- Decision: Prefer `src` layout (`src/dearcyfi/...`) to prevent accidental imports from repository root during development.
- Decision: Use `pyproject.toml` with setuptools build backend for packaging metadata and build configuration.
- Decision: Keep a compatibility strategy for existing imports (short-term shim or documented migration) to reduce breakage.

## Alternatives Considered
- Flat/top-level packaging with `py_modules` plus mixed packages.
- Why not chosen: lower migration effort, but easier to accidentally depend on repository-root import behavior and harder to maintain long term.

## Risks / Trade-offs
- Risk: Import-path breakage for existing users.
- Mitigation: Provide migration notes and optional temporary compatibility shim.
-
- Risk: Hidden dependency mismatches between `requirements.txt` and runtime imports.
- Mitigation: Perform explicit import audit and reconcile metadata before release.
-
- Risk: Refactor noise from module moves.
- Mitigation: Keep changes scoped to packaging and import paths; avoid unrelated code edits.

## Migration Plan
1. Introduce package metadata and namespace.
2. Move/update runtime modules and imports.
3. Validate editable install and artifact install.
4. Update README usage examples.
5. Deprecate old import style through documentation (and optional temporary shim if retained).

## Open Questions
- Should legacy import `from DearCyFi import DearCyFi` remain supported for one transition release?
- Should demo files be shipped as package extras/examples or stay repository-only?
- Should notebooks be excluded from distribution artifacts by default?
