# Examples

This folder contains example applications for DearCyFi.

## Keyboard Shortcut Input Probe

Run `python examples/ctrl_z_probe.py` with DearCyGui installed. Click the
window and try Ctrl+Z, Ctrl+Y, Ctrl+C, Ctrl+V, Ctrl+A, and Ctrl+X. The counters
and console report detected presses; no editing or clipboard actions are performed.

## External Demo Repository

The primary demo lives in the git submodule below:

- `examples/DearCyFi_Demo`
- GitHub: https://github.com/khazaddim/DearCyFi_Demo

If you cloned this repo without submodules, initialize it with:

```bash
git submodule update --init --recursive
```
