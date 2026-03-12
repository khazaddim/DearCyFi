# DearCyFi
DearCyFi is a specialized financial charting widget for use in the DearCyGui GUI library.

## Demo

The primary demo app is maintained in a separate repository:

- https://github.com/khazaddim/DearCyFi_Demo
- Included in this repo as a submodule at `examples/DearCyFi_Demo`

If you cloned this repo without submodules, initialize it with:

```bash
git submodule update --init --recursive
```

## Install

Editable install for development:

```bash
python -m pip install -e .
```

Standard install from source tree:

```bash
python -m pip install .
```

## Quick Import Check

```python
from dearcyfi import DearCyFi
```
