---
name: dearcygui-build
description: "Use when: building DearCyGui from source, rebuilding after editing .pyx/.pxd files, debugging build failures, running the demo/tests after a code change, or invoking Python against the freshly-built extension on this workspace. Covers the Cython + setuptools + CMake (SDL3) build pipeline and the Windows venv conventions used here."
---

# DearCyGui Build Workflow

Use this skill whenever you have edited any Cython source (`.pyx` or `.pxd`) under `dearcygui/` and need to recompile the extension, or when you need to run Python code that imports `dearcygui` after a change.

## When To Use

- "rebuild" / "build" / "recompile" after editing `.pyx` or `.pxd`
- Running the demo (`Small_Input_Demo.py`) or tests after code changes
- Diagnosing `ModuleNotFoundError: No module named 'dearcygui.dearcygui'`
- Diagnosing Cython compile errors, linker errors, or SDL3 build issues
- Any task that involves importing `dearcygui` from Python on this workspace

## Environment (Windows / this workspace)

- **Repo root:** `C:\Chris\DearCyGui`
- **Venv:** `C:\Chris\DearCyGui\.venv` (Python 3.14, cp314)
- **Venv Python (absolute):** `C:\Chris\DearCyGui\.venv\Scripts\python.exe`
- **PowerShell activation:** `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned; & .\.venv\Scripts\Activate.ps1`
- **Build deps** (declared in `pyproject.toml`, must be pre-installed in venv when using `--no-build-isolation`): `Cython==3.1.6`, `wheel`, `click`, `setuptools`, `cmake`. Note: Cython 3.1.2 is known to fail; 3.1.6 works.
- **Native toolchain:** MSVC (Visual Studio Build Tools, "Desktop development with C++"). MinGW path exists in `setup.py` but is disabled.

## Canonical Build Command

```powershell
C:\Chris\DearCyGui\.venv\Scripts\python.exe -m pip install --no-build-isolation . --force-reinstall --no-cache-dir
```

Why each flag:

- `--no-build-isolation`: build runs against the venv's already-installed Cython/setuptools/cmake (faster, reproducible). Requires those deps to be present in the venv.
- `--force-reinstall`: ensures the wheel is reinstalled even when version string didn't change.
- `--no-cache-dir`: avoids pip caching a stale wheel from a previous build.
- `.`: build from the current directory (the repo root).

The build does several phases:
1. **CMake** builds SDL3 (static) into `build_SDL/` and FreeType into `build_FT/`.
2. **Cython** transpiles every `.pyx` under `dearcygui/` → `.cpp`.
3. **setuptools / MSVC** compiles the `.cpp` files + hand-written backend C++ into the extension module.
4. **pip** installs the resulting wheel into the venv's `site-packages`.

The full rebuild takes several minutes on Windows. The SDL3 / FreeType CMake phases are cached and skip on re-runs unless their `build_*/` folders are deleted.

## Build Flags (optional)

Pass to `pip install` via `--config-settings` or directly to `setup.py`. From [setup.py](setup.py):

- `--msvc-compat` — when using MinGW, emit MSVC-compatible flags (`-fms-extensions`, etc.).
- `--gcc-clang-compat` — extra GCC/Clang interop flags.

Neither is needed on a stock MSVC setup.

## Running Python After A Build

**CRITICAL:** Do NOT run Python from the repo root with bare `python script.py`. The repo root contains a `dearcygui/` source folder, so `import dearcygui` resolves to the *source* (no compiled extension), producing:

```
ModuleNotFoundError: No module named 'dearcygui.dearcygui'
```

Two safe patterns:

1. **Use the venv Python by absolute path from any cwd:**
   ```powershell
   C:\Chris\DearCyGui\.venv\Scripts\python.exe path\to\script.py
   ```
   pip-install puts the compiled package in `.venv\Lib\site-packages\dearcygui\`, which the venv Python finds first when cwd is anywhere except the repo root.

2. **Run from the repo root only after sys.path massaging.** `Small_Input_Demo.py` does this: it removes the repo root from `sys.path` and prepends `.venv\Lib\site-packages` before `import dearcygui`.

Tool-launched fresh terminals do NOT inherit venv activation from the user's interactive session — always invoke the venv Python by absolute path in agent terminals, or re-run the activation incantation.

## Runtime Probe Scripts

Keep these repo-root probe scripts around for native crash isolation after a successful build:

- `tmp_bare_window.py` — opens a bare DearCyGui window with a trivial widget and bounded viewport loop. Use this first to answer: "is the viewport/window loop healthy at all?"
- `tmp_plotcolorbars_minimal.py` — opens a minimal plot containing a single `PlotColorBars` item while importing the installed package instead of the source tree. Use this to answer: "is the crash in the core `PlotColorBars` renderer itself, or only in the full demo/update logic?"

Both scripts deliberately remove the repo root from `sys.path` and prepend the venv `site-packages` path before importing `dearcygui`, so they test the freshly installed extension rather than the source folder shadow.

Recommended usage order for runtime crashes after a rebuild:

1. Run `tmp_bare_window.py`.
2. If that passes, run `tmp_plotcolorbars_minimal.py`.
3. If that passes, run the full demo such as `PlotColorBars_Demo.py`.

This staged narrowing is cheaper and more informative than jumping straight into the full demo.

## Generated Files (gitignore policy)

Cython emits `.cpp` next to each `.pyx`. These are build artifacts and must not be committed:

- `dearcygui/*.cpp` — gitignored.
- `dearcygui/utils/*.cpp` — gitignored.
- `cython_learning/*.cpp` — gitignored.

Hand-written C++ that IS tracked:

- `dearcygui/backends/imgui_impl_opengl3.cpp`
- `dearcygui/backends/imgui_impl_sdl3.cpp`
- `dearcygui/backends/sdl3_gl3_backend.cpp`

If a regenerated `.cpp` appears as modified in `git status`, the rule of thumb is: it's a build artifact, leave it unstaged. If it's under `dearcygui/utils/` or top-level `dearcygui/` it should already be gitignored; if it shows up anyway, check the `.gitignore` patterns (recursive globs are NOT used — each subdirectory needs its own rule).

## Common Failure Modes

- **`ModuleNotFoundError: No module named 'dearcygui.dearcygui'`** — running from repo root with bare `python`. Fix: use venv Python absolute path from a different cwd.
- **`NameError` on a Cython `cpdef enum class` (e.g. `GamepadButton`)** — inside `.pyx` files, bare `EnumName(int_value)` is not callable at Python runtime without an explicit import. Use the helper `make_EnumName(int_value)` (defined alongside the enum in `dearcygui/types.pxd`) or cimport the enum.
- **Cython 3.1.2 build error** — pin Cython to 3.1.6 in the venv.
- **SDL3 CMake fails on first build** — make sure `cmake` is installed in the venv (`pip install cmake`) and a C++ compiler is available on PATH (MSVC Build Tools on Windows).
- **Stale extension after `.pxd` edit** — `.pxd` changes affect every `.pyx` that cimports from it, plus their transitive consumers. The canonical command rebuilds everything; do not try to partial-rebuild a single file.
- **Stale generated C++ after branch integration** — if MSVC reports an error in a generated file (`dearcygui/core.cpp`, `dearcygui/plot.cpp`, etc.) for code that is not present in the current `.pyx` source, the generated `.cpp` is stale. Example symptom: `core.cpp` references `platformViewport.activityDetected` while current `core.pyx` uses `needsRender.store(True)`. Force Cython regeneration by updating `.pyx` timestamps, then rebuild:
   ```powershell
   Get-ChildItem dearcygui -Filter *.pyx | ForEach-Object { $_.LastWriteTime = Get-Date }
   Get-ChildItem dearcygui\utils -Filter *.pyx | ForEach-Object { $_.LastWriteTime = Get-Date }
   C:\Chris\DearCyGui\.venv\Scripts\python.exe -m pip install --no-build-isolation . --force-reinstall --no-cache-dir
   ```
   After a successful build, discard generated/build artifact changes (`build_FT/`, `build_SDL/`, `dearcygui/*.cpp`, `dearcygui/utils/*.cpp`, `dearcygui.egg-info/`) unless intentionally updating generated artifacts.
- **Native crash with no Python traceback** — after rebuilding, do not jump straight to the full app. First run the retained probe scripts in order: `tmp_bare_window.py`, then `tmp_plotcolorbars_minimal.py`, then the full demo. If the bare window passes and the minimal plot fails, the fault is in plot rendering rather than viewport startup.
- **Venv not activated in agent terminal** — symptom: `python` resolves to system Python and `import dearcygui` finds nothing or the wrong build. Fix: always use `C:\Chris\DearCyGui\.venv\Scripts\python.exe` by absolute path.

## Recommended Agent Workflow

When the user asks you to rebuild and test:

1. Edit the `.pyx` / `.pxd` files.
2. Run the canonical build command (sync mode, generous timeout — at least 10 min).
3. On success, prefer the smallest relevant runtime check first: `tmp_bare_window.py`, `tmp_plotcolorbars_minimal.py`, then the full demo or test.
4. Do NOT stage regenerated `.cpp` files — they're either gitignored or by-convention untracked.

After branch integration, if native compiler errors mention generated `.cpp` code that no longer exists in the corresponding `.pyx`, force Cython regeneration before changing source semantics. The first real error may be stale code, not a logic bug.

When the user reports a build failure, surface the **first** Cython/compiler error from the log (later errors are usually downstream cascades) and ask before attempting fixes that change source semantics.
