"""Standalone DearCyGui probe for common Ctrl keyboard shortcuts."""

import dearcygui as dcg


SHORTCUTS = (
    (dcg.Key.Z, "Undo"),
    (dcg.Key.Y, "Redo"),
    (dcg.Key.C, "Copy"),
    (dcg.Key.V, "Paste"),
    (dcg.Key.A, "Select all"),
    (dcg.Key.X, "Cut"),
)


class ShortcutProbe:
    def __init__(self):
        self.context = dcg.Context()
        self.counts = {key: 0 for key, _ in SHORTCUTS}
        self.status = {}

        with dcg.Window(self.context, label="Keyboard shortcut probe", primary=True):
            dcg.Text(self.context, value="Click this window and try the shortcuts below.")
            dcg.Text(self.context, value="Each press is counted once; holding a key does not repeat.")
            dcg.Text(self.context, value="Detection only: no clipboard or editing actions are performed.")
            for key, action in SHORTCUTS:
                self.status[key] = dcg.Text(
                    self.context, value=f"Ctrl+{key.name} ({action}): 0"
                )

    def render_frame(self):
        self.context.viewport.render_frame()
        ctrl_down = (
            self.context.is_key_down(dcg.Key.LEFTCTRL)
            or self.context.is_key_down(dcg.Key.RIGHTCTRL)
        )
        if ctrl_down:
            for key, action in SHORTCUTS:
                if self.context.is_key_pressed(key, repeat=False):
                    self.counts[key] += 1
                    self.status[key].value = f"Ctrl+{key.name} ({action}): {self.counts[key]}"
                    print(self.status[key].value, flush=True)


def main():
    probe = ShortcutProbe()
    probe.context.viewport.initialize(title="Keyboard shortcut probe", width=600, height=300)
    while probe.context.running:
        probe.render_frame()


if __name__ == "__main__":
    main()
