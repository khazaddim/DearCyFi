"""Manual probe for native and plot-owned context-menu entries."""

import argparse

import dearcygui as dcg
import dearcygui.dearcygui as dcg_native


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--custom", action="store_true", help="Attach custom menu children")
    parser.add_argument("--no-menus", action="store_true", help="Disable the native plot menus")
    parser.add_argument("--middle-button", action="store_true", help="Use middle-click for plot menus")
    parser.add_argument("--smoke", action="store_true", help="Render three hidden frames and exit")
    args = parser.parse_args()

    context = dcg.Context()
    print(f"DearCyGui loaded from: {dcg.__file__}", flush=True)
    print(f"Compiled extension loaded from: {dcg_native.__file__}", flush=True)

    with dcg.Window(context, label="Plot context-menu probe", primary=True):
        dcg.Text(context, value="Open each plot's canvas menu. Native options must remain available.")
        dcg.Text(context, value="Custom mode: check each submenu and callback count; reopen each menu.")
        status = dcg.Text(context, value="Callbacks: none")
        counts = {"A": 0, "B": 0}

        def action(name, kind):
            counts[name] += 1
            message = f"Plot {name}, {kind}: {counts[name]} callback(s)"
            status.value = message
            print(message, flush=True)

        for name in ("A", "B"):
            with dcg.Plot(
                context,
                label=f"Plot {name}",
                width="fillx",
                height=260,
                no_menus=args.no_menus,
                menu_button=dcg.MouseButton.MIDDLE if args.middle_button else dcg.MouseButton.RIGHT,
            ) as plot:
                dcg.PlotLine(context, label=f"Series {name}", X=[0, 1, 2], Y=[0, 1, 0])
                if args.custom:
                    with dcg.Menu(context, parent=plot, label=f"Probe {name}"):
                        dcg.MenuItem(
                            context,
                            label=f"Run {name}",
                            callback=lambda *_, n=name: action(n, "direct"),
                        )
                        dcg.MenuItem(
                            context,
                            label=f"Toggle {name}",
                            check=True,
                            callback=lambda sender, target, checked, n=name:
                                action(n, "checked" if checked else "unchecked"),
                        )
                        with dcg.Menu(context, label="Nested"):
                            dcg.MenuItem(
                                context,
                                label=f"Nested {name}",
                                callback=lambda *_, n=name: action(n, "nested"),
                            )

    context.viewport.initialize(
        title="Plot context-menu probe",
        width=900,
        height=760,
        visible=not args.smoke,
    )
    if args.smoke:
        for _ in range(3):
            context.viewport.render_frame()
        print("Rendered three hidden frames; popup interactions were not tested.", flush=True)
    else:
        while context.running:
            context.viewport.render_frame()


if __name__ == "__main__":
    main()
