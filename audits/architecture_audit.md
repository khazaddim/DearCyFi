# DearCyFi Architecture Audit

**Scope:** Commit `d9b02cb6cbb9e31630cf55f09bd7bd009bc96b0d` through the current `DCG-Mod` branch  
**Date:** 2026-08-15  
**Focus:** Cross-file feature changes, refactoring needs, and readiness for moving averages and interactive technical-analysis overlays

## Executive Summary

DearCyFi does not need a rewrite or a feature freeze. Most recent cross-file changes are healthy vertical feature slices: econometric support needed a renderer, collapse coordination, projection behavior, exports, demo integration, and tests; Y-axis assignment needed propagation through each composite renderer; colored bars necessarily crossed the DearCyFi and DearCyGui boundary because the underlying primitive changed.

The architectural concern is more specific: [`core.py`](../src/dearcyfi/core.py) has accumulated too many unrelated responsibilities. It coordinates registered time series and gap collapse while also owning candle convenience state, time-axis formatting, date-context repair, label-overlap diagnostics, and resize-driven axis mutation. This concentration largely predates the recent features, but continued growth will make new work harder to test and reason about.

**Verdict:** Proceed with new features while performing small, targeted refactors at the boundaries those features exercise. Preserve the existing structural time-series protocol. Do not force computed series and interactive drawing tools into one inheritance hierarchy.

## Evidence

Since the selected baseline:

- [`core.py`](../src/dearcyfi/core.py) grew from 756 to 989 lines.
- [`DCG_Candle_Utils.py`](../src/dearcyfi/DCG_Candle_Utils.py) grew from 485 to 558 lines.
- [`econometric_series.py`](../src/dearcyfi/econometric_series.py) was added as a focused 198-line module.
- The current source contains a reusable gap-collapse implementation in [`gap_utils.py`](../src/dearcyfi/candle_utils/gap_utils.py).
- Three completed OpenSpec changes remain active rather than archived, while [`openspec/project.md`](../openspec/project.md) still describes an older, candle-focused architecture.

Validation during the audit produced:

- **19 passing tests** for independent gap projection, econometric-series behavior, and provider contracts.
- **46 passing and 16 failing tests** in the full suite.
- All 16 full-suite failures were caused by the installed DearCyGui package lacking `PlotColorBars`, not by independent failures in gap projection or econometric synchronization.

## Healthy Architecture

### Structural Time-Series Protocol

`DearCyFi.register_time_series()` relies on a small behavioral contract:

- `source_dates`
- `set_plot_dates()`
- `restore_source_dates()`

This is the correct extension point for data-backed series. It keeps gap projection independent of concrete renderer types and avoids premature inheritance between candles, econometric lines, and future computed series.

`PlotCandleStick` participates through `_CandleSeriesAdapter`; `PlotEconometricSeries` implements the behavior directly. Tests in [`test_collapse_coordination.py`](../tests/test_collapse_coordination.py) and [`test_gap_projection.py`](../tests/test_gap_projection.py) support this design.

### Isolated Gap Projection

`GapCollapseManager` owns gap detection, collapse-map construction, projection, and restoration. It is reusable and does not need to know how a series renders itself. This separation should be preserved.

### Focused Econometric Renderer

[`econometric_series.py`](../src/dearcyfi/econometric_series.py) owns native line/scatter rendering, source and plot dates, value validation, and observation tooltips. Adding this as a separate module was healthy organization, not evidence that every feature is excessively coupled.

### Composite Axis Propagation

Candles, volume bars, econometric lines, scatter markers, and interaction elements each need the selected Y-axis. Touching more than one renderer for per-series axis support was therefore expected. The tests in [`test_series_axis_assignment.py`](../tests/test_series_axis_assignment.py) validate this behavior.

## Refactoring Needs

### 1. Split Time-Axis and Diagnostic Work from `DearCyFi`

**Priority:** Medium-high

`axes_resize_callback()` combines several responsibilities:

- tick generation and formatting
- collapsed-coordinate expansion
- label grouping and overlap detection
- date-context repair
- diagnostic-series creation and updates
- direct X-axis mutation

Extract pure label calculation and date-context repair first, with tests. Diagnostic rendering can then become a small coordinator or optional component. Keep `DearCyFi` responsible for wiring the resize event, not for implementing every stage.

This is the highest-value internal refactor because the logic is complex, stateful, and weakly isolated by tests.

### 2. Make the Series Contract Explicit

**Priority:** Medium

Keep structural typing, but express the existing contract with `typing.Protocol`. The protocol should cover only behavior needed by time-coordinate coordination. A minimal shape is:

```python
class TimeCoordinateSeries(Protocol):
    @property
    def source_dates(self) -> np.ndarray: ...

    def set_plot_dates(self, dates: np.ndarray) -> None: ...

    def restore_source_dates(self) -> None: ...
```

Do not include renderer-specific methods, tooltip behavior, or axis ownership unless a concrete use case requires them.

### 3. Clarify Registration Lifecycle

**Priority:** Medium

Candles are registered automatically by `set_data()`, while econometric series are constructed and registered manually. Both patterns are defensible, but lifecycle rules should be explicit:

- who owns a registered series
- whether replacement restores the old series first
- what unregistration does while time is collapsed
- how a failed multi-series projection rolls back
- how the collapse source changes when its series is removed

A small registry object may become worthwhile if this logic grows further. It should be extracted only with the current coordination tests carried over, rather than introduced as a broad plugin framework.

### 4. Centralize Small Proven Duplications

**Priority:** Low-medium

Y-axis validation is duplicated between candle and econometric renderers. Move this rule to a focused internal helper so accepted axes and error behavior cannot drift.

Date ownership also needs a documented contract. Each renderer should retain immutable source coordinates and independently mutable plot coordinates. Tests should verify that collapse and restoration never corrupt source dates and that caller-owned arrays cannot unexpectedly mutate rendered state.

Avoid introducing a shared renderer base class at this stage. Candles and scalar line series have different child structures, update semantics, and interaction behavior. A base class would currently couple more than it simplifies.

### 5. Resolve Y2 Diagnostic Ownership

**Priority:** Medium before broader axis use

Diagnostics currently use Y2 while public series APIs also permit Y2. Define whether diagnostics reserve that axis, share it, use a non-data drawing layer, or allocate an internal axis dynamically. Add a mixed-axis test before moving averages or indicators begin using secondary axes routinely.

## Feature Guidance

### Moving Averages and Other Computed Series

A moving average belongs in the existing registered time-series path. It should:

1. Compute values from source observations outside the gap-projection layer.
2. Retain original timestamps separately from displayed timestamps.
3. Implement the structural time-coordinate protocol.
4. Own its renderer and tooltip behavior in a focused module.
5. Register with `DearCyFi` for coordinated collapse and restoration.

The first moving-average implementation is a useful test of the protocol. If it requires modifications throughout `core.py`, that is evidence the registration boundary still leaks. It should not require a general-purpose plugin system first.

### Fibonacci and Other Interactive Drawing Tools

A Fibonacci retracement is not a data series. It has draggable anchors, hit regions, derived levels, selection state, and a different lifecycle from source-backed observations.

Build technical drawing tools through a separate drawing/annotation path using DearCyGui interaction primitives. Their contract may eventually include operations such as attach, detach, select, and update geometry, but they should not be registered as time series merely to reuse coordinate handling.

When collapsed time affects an anchor, use an explicit coordinate mapper supplied by the chart. Do not expose the full series registry or gap manager to drawing tools.

## Recommended Sequence

1. Make the custom DearCyGui dependency and CI environment reproducible.
2. Archive completed OpenSpec changes and update the canonical project architecture documentation.
3. Extract and test pure time-axis label and date-context calculations.
4. Add a minimal structural protocol for registered time-coordinate series.
5. Centralize Y-axis validation and define diagnostic-axis ownership.
6. Implement one moving-average series as a proof of the extension boundary.
7. Design interactive drawing lifecycle separately when Fibonacci work begins.

## Reproducibility Blocker

[`pyproject.toml`](../pyproject.toml) declares ordinary `dearcygui`, but the active branch requires a custom build with `dcg.PlotColorBars`. A README warning does not make that dependency reproducible.

A clean developer machine and CI should install one exact tested DearCyGui revision and verify the required capability before running DearCyFi tests.

### What Continuous Integration Means

Continuous integration (CI) is a clean computer that GitHub creates temporarily whenever selected repository events occur. The computer follows commands stored in a YAML file under `.github/workflows/`, reports whether every command succeeded, and is then discarded.

For DearCyFi, CI should answer these questions on both Windows and Linux:

1. Can a new machine download the exact custom DearCyGui source and all its submodules?
2. Can it compile DearCyGui without relying on files or settings from a developer workstation?
3. Does the resulting package provide `PlotColorBars`?
4. Can DearCyFi install against that package?
5. Does the DearCyFi test suite pass?

CI does not deploy or publish anything in the initial design. It only builds and tests. GitHub displays a green check when both operating-system jobs pass and a red check when a command fails. The log for the failed step is available from the repository's **Actions** tab.

### Pinning the Custom DearCyGui Revision

A branch name such as `Game_Controller_Build` is a moving label. New commits can change what that name resolves to, which means two builds made on different days may compile different source. A commit SHA is an immutable identifier for one exact repository state.

The custom checkout inspected for this audit is:

```text
Repository: https://github.com/khazaddim/DearCyGui
Branch:     Game_Controller_Build
Commit:     18af9ced0f99e0ed3d9683b241525189d0876345
```

That commit is pushed to `origin/Game_Controller_Build`, its working tree was clean during inspection, and its Cython source and declarations contain `PlotColorBars`. Its `.gitmodules` file uses non-interactive HTTPS URLs and records exact submodule revisions.

Treat this SHA as a **candidate pin until the workflow below passes on both operating systems**. A source commit containing the class is necessary, but the green CI run is the evidence that the complete revision builds and works in clean environments.

The pin should have one obvious source of truth. Initially, put it directly in the GitHub Actions checkout step. Do not put the fork URL in DearCyFi's normal runtime dependencies yet: that would force every user installation to compile a large native project from source. Once custom wheels are published, DearCyFi can depend on an appropriate released version instead.

To choose a newer pin later:

1. Build and test the desired DearCyGui commit locally.
2. Commit and push all required DearCyGui source changes.
3. Confirm that `git status --short` is empty in the DearCyGui checkout.
4. Obtain the identifier with `git rev-parse HEAD`.
5. Replace the `ref` value in the workflow.
6. Push the DearCyFi change and wait for both CI jobs to pass.

Never pin uncommitted local changes: GitHub cannot download files that exist only on `C:\Chris\DearCyGui`.

### Recommended First GitHub Actions Workflow

Create `.github/workflows/ci.yml` in DearCyFi with the following content when CI implementation begins:

```yaml
name: CI

on:
    push:
        branches: [main, DCG-Mod]
    pull_request:
    workflow_dispatch:

permissions:
    contents: read

jobs:
    build-and-test:
        name: ${{ matrix.os }} / Python 3.12
        runs-on: ${{ matrix.os }}
        strategy:
            fail-fast: false
            matrix:
                os: [windows-2025, ubuntu-22.04]

        steps:
            -
                name: Check out DearCyFi
                uses: actions/checkout@v4
                with:
                    submodules: recursive

            -
                name: Check out pinned custom DearCyGui
                uses: actions/checkout@v4
                with:
                    repository: khazaddim/DearCyGui
                    ref: 18af9ced0f99e0ed3d9683b241525189d0876345
                    path: .deps/DearCyGui
                    submodules: recursive

            -
                name: Set up Python
                uses: actions/setup-python@v5
                with:
                    python-version: "3.12"
                    cache: pip

            -
                name: Enable the MSVC compiler
                if: runner.os == 'Windows'
                uses: ilammy/msvc-dev-cmd@v1

            -
                name: Install Linux native dependencies
                if: runner.os == 'Linux'
                run: |
                    sudo apt-get update
                    sudo apt-get install -y \
                        build-essential \
                        libegl1-mesa-dev \
                        libgl1-mesa-dev \
                        libwayland-dev \
                        libx11-dev \
                        libxcursor-dev \
                        libxext-dev \
                        libxfixes-dev \
                        libxi-dev \
                        libxkbcommon-dev \
                        wayland-protocols \
                        xvfb

            -
                name: Install Python build tools
                run: |
                    python -m pip install --upgrade pip
                    python -m pip install Cython==3.1.6 wheel click setuptools cmake pytest

            -
                name: Build and install custom DearCyGui
                run: python -m pip install --no-build-isolation ./.deps/DearCyGui

            -
                name: Verify the custom capability
                run: python -c "import dearcygui as dcg; assert hasattr(dcg, 'PlotColorBars'), 'Pinned DearCyGui build lacks PlotColorBars'"

            -
                name: Install DearCyFi
                run: python -m pip install -e .

            -
                name: Run tests on Windows
                if: runner.os == 'Windows'
                run: python -m pytest -q

            -
                name: Run tests on Linux
                if: runner.os == 'Linux'
                run: xvfb-run -a python -m pytest -q
```

### Why the Workflow Has Separate Windows and Linux Setup

The matrix runs the same job twice. Most steps are shared, but native compilation differs:

- **Windows:** `ilammy/msvc-dev-cmd` places the Visual Studio C/C++ compiler on `PATH`. GitHub's Windows image already contains Visual Studio Build Tools; the action activates the compiler environment for later steps.
- **Linux:** `apt-get` installs GCC/G++, OpenGL/EGL, X11, Wayland, keyboard, cursor, and related development headers needed while compiling SDL and DearCyGui.
- **Linux test display:** GitHub's Ubuntu runner has no physical monitor. `xvfb-run` provides a temporary virtual X display for tests that initialize graphical APIs.
- **Both systems:** Cython is pinned to `3.1.6`, the version recorded by the custom build configuration. `--no-build-isolation` ensures the build uses those explicitly installed tools.

The Linux package list is based on DearCyGui's existing [`build.yml`](https://github.com/khazaddim/DearCyGui/blob/18af9ced0f99e0ed3d9683b241525189d0876345/.github/workflows/build.yml), which already builds `manylinux_2_34` wheels and installs the corresponding X11, OpenGL/EGL, Wayland, cursor, input, and keyboard development packages inside its build container. That workflow uses `yum` package names because `cibuildwheel` runs in a manylinux container; the DearCyFi test workflow uses the equivalent `apt` package names because it runs directly on Ubuntu.

Python 3.12 is a conservative first CI target supported by DearCyGui. After one version is consistently green, a Python-version matrix can be added. Testing many Python versions immediately would multiply build time and make initial failures harder to diagnose.

### What Each Checkout Does

The first `actions/checkout` downloads DearCyFi, including its demo submodule. The second downloads a separate repository into `.deps/DearCyGui` at the exact pinned commit. `submodules: recursive` is essential because DearCyGui compiles vendored SDL, FreeType, ImGui, ImPlot, and other native dependencies at their recorded revisions.

The workflow intentionally builds DearCyGui from source on each operating system. This proves the source pin is reproducible. It is slower than installing a wheel, but it is the right first stage while the custom fork is under development.

### GitHub Setup Steps

1. Add and commit `.github/workflows/ci.yml` on the DearCyFi branch.
2. Push that branch to GitHub.
3. Open the DearCyFi repository on GitHub and select the **Actions** tab.
4. Select the **CI** workflow to view its Windows and Linux jobs.
5. Open a failed job, then expand the first red step to read its compiler or test output.
6. The `workflow_dispatch` trigger also adds a **Run workflow** button for manual runs.

If both repositories are public, the standard read-only `GITHUB_TOKEN` and `contents: read` permission should be sufficient. If the DearCyGui fork is private, checking out a second private repository requires a separate read-only personal access token stored as a DearCyFi Actions secret. Do not put a token directly in YAML or commit it to the repository.

### Expected First-Run Behavior

The first run may take several minutes per operating system because DearCyGui builds SDL, FreeType, generated Cython C++, and the extension itself. Diagnose failures from the first red step:

- **Checkout or submodule failure:** verify repository visibility, the pinned SHA, HTTPS submodule URLs, and token access.
- **Cython failure:** verify `Cython==3.1.6` was installed and the build uses `--no-build-isolation`.
- **Compiler or missing-header failure:** adjust only the operating-system dependency step.
- **Capability probe failure:** the wrong DearCyGui revision or package was installed; do not continue to DearCyFi tests.
- **Display error on Linux:** confirm the test command is wrapped in `xvfb-run -a`.
- **DearCyFi test failure:** the native dependency built and imported correctly, so investigate the first failing DearCyFi test.

Do not add build caches until this uncached workflow passes reliably. Caching Cython, CMake, or compiled native outputs too early can conceal stale-build problems. Pip's download cache is safe and is enabled by `actions/setup-python`.

### From Source Builds to Published Wheels

The source-build workflow is the first milestone, not necessarily the permanent installation method. A later release pipeline in the DearCyGui fork can use `cibuildwheel` to build Windows and manylinux wheels, upload them as artifacts, and eventually publish versioned wheels. DearCyFi CI could then install an exact wheel version in seconds instead of recompiling DearCyGui.

DearCyGui's existing wheel workflow should be the starting point for that release pipeline. It already defines Linux wheel targets for supported CPython versions, a `manylinux_2_34` image, native build packages, Windows wheel jobs, and artifact upload. The custom fork should first run that workflow unchanged at the pinned commit, then make only capability-specific adjustments required by `PlotColorBars` or other fork changes. DearCyFi should not duplicate the wheel-building logic; it should consume and test the resulting artifact.

Keep these concerns separate:

- **DearCyGui workflow:** compile and test the native package, then produce wheels.
- **DearCyFi workflow:** install one approved DearCyGui revision or wheel and test the charting package against it.

Until wheels are published, the source checkout plus exact SHA is the clearest reproducible contract.

### Minimum Local Equivalent

The CI sequence can be approximated locally after checking out the pinned DearCyGui source and its submodules:

```powershell
python -m pip install Cython==3.1.6 wheel click setuptools cmake pytest
python -m pip install --no-build-isolation C:\path\to\DearCyGui
python -c "import dearcygui as dcg; assert hasattr(dcg, 'PlotColorBars')"
python -m pip install -e .
python -m pytest -q
```

Passing locally is useful, but it is not a substitute for CI: the GitHub runner proves the build does not depend on an existing `.venv`, cached CMake output, generated C++ files, or workstation-only configuration.

## Tests to Add

- Pure tests for label overlap detection.
- Parametrized tests for date-context repair.
- Collapsed-time tick relabeling tests.
- Registration replacement and unregistration while collapsed.
- Rollback behavior when one registered series rejects projected dates.
- Source-date immutability and input-array ownership.
- User series and diagnostics sharing or separating secondary axes.
- A protocol-contract test reused by every registered series type.

## Conclusion

The number of files changed by a feature is not itself a coupling problem. DearCyFi's recent changes generally crossed appropriate boundaries and produced focused modules and tests. The real risk is continued concentration inside `DearCyFi`, especially resize-driven axis and diagnostic behavior, plus implicit lifecycle and dependency contracts.

Proceed incrementally. Strengthen the existing time-series boundary, extract the most complex pure logic from `core.py`, and keep interactive drawing tools architecturally separate from data series. This lowers future feature cost without destabilizing working code.
