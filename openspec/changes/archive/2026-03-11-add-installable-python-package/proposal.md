# Change: Make DearCyFi Installable via Pip

## Why
DearCyFi is currently a script-style repository and cannot be installed and consumed as a standard Python package using `pip install` or `pip install -e .`.

Packaging it as an installable distribution improves reuse, dependency management, and integration into downstream applications.

## What Changes
- Add Python packaging metadata and build configuration for an installable distribution.
- Define a supported package layout and import path strategy for public consumption.
- Ensure internal modules resolve correctly when installed, not only when run from repository root.
- Define package dependency declarations aligned with runtime imports.
- Document installation and basic verification workflow.
- Mark migration expectations for existing import paths if package namespace changes.

## Impact
- Affected specs: `packaging`
- Affected code:
  - Repository packaging metadata (`pyproject.toml` and related metadata files)
  - Import paths in `DearCyFi.py`, utility modules, and demo script
  - Dependency declarations (`requirements` and package metadata)
  - README installation and usage guidance
