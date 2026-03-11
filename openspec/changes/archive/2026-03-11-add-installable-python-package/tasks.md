## 1. Finalize Packaging Design
- [x] 1.1 Decide and document package layout (`src/dearcyfi` preferred) and the canonical public import (`from dearcyfi import DearCyFi`).
- [x] 1.2 Define migration policy for existing top-level imports (`from DearCyFi import DearCyFi`) and whether compatibility shims will be provided.
- [x] 1.3 Confirm minimum supported Python version and build backend (`setuptools` with PEP 517/518).

## 2. Create Packaging Metadata
- [x] 2.1 Add `pyproject.toml` with project metadata: name, version, description, readme, license, authors, python requirement, dependencies.
- [x] 2.2 Configure package discovery for chosen layout and include package data settings if needed.
- [x] 2.3 Add minimal package entrypoint (`__init__.py`) exposing the main public API.

## 3. Restructure Modules for Installability
- [x] 3.1 Move or mirror runtime modules under the package namespace (core plot class, candle/bar utilities, locator package, gap utilities).
- [x] 3.2 Add `__init__.py` files for importable package directories.
- [x] 3.3 Update absolute local imports to package-qualified or explicit relative imports to avoid repository-root coupling.
- [x] 3.4 Ensure demo code imports via the canonical package path.

## 4. Dependency Alignment
- [x] 4.1 Audit imports across runtime modules and produce authoritative runtime dependency list.
- [x] 4.2 Update package dependencies to match actual imports (including `pandas`/`pytz` usage where applicable).
- [x] 4.3 Reconcile `requirements.txt` with package metadata and fix mismatches/typos.

## 5. Build and Install Verification
- [x] 5.1 In a clean environment, run editable install: `python -m pip install -e .`.
- [x] 5.2 Run wheel/sdist build: `python -m build`.
- [x] 5.3 Install built artifact in a clean environment and run smoke import for public API.
- [x] 5.4 Run a minimal runtime check that instantiates `DearCyFi` dependencies enough to catch missing package modules.

## 6. Documentation and Upgrade Notes
- [x] 6.1 Update README with install instructions for editable and standard installs.
- [x] 6.2 Add a minimal usage snippet showing canonical import path.
- [x] 6.3 Document migration notes for any changed import paths.

## 7. Final Quality Gate
- [x] 7.1 Re-run OpenSpec validation for this change.
- [x] 7.2 Verify all tasks are complete and checkboxes reflect actual completion state.
