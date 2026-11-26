import asyncio
import importlib.util
from pathlib import Path
from types import MethodType, SimpleNamespace

import dearcygui as dcg

from dearcyfi import PlotEconometricSeries


def test_legend_menus_identify_each_series_independently(monkeypatch):
    demo_dir = Path(__file__).parents[1] / "examples" / "DearCyFi_Demo"
    monkeypatch.syspath_prepend(str(demo_dir))
    monkeypatch.setattr(asyncio, "set_event_loop", lambda loop: None)
    spec = importlib.util.spec_from_file_location("dearcyfi_demo_legend_test", demo_dir / "DearCyFi_Demo.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.loop.close()

    context = dcg.Context()
    messages = []
    host = SimpleNamespace(C=context, _legend_test_series={}, set_status=messages.append)
    host._identify_legend_series = MethodType(module.DearCyFiDemo._identify_legend_series, host)
    with dcg.Window(context):
        with dcg.Plot(context, label="Plot"):
            first = PlotEconometricSeries(context, dates=[1, 2], values=[3, 4], label="SMA 20")
            second = PlotEconometricSeries(context, dates=[1, 2], values=[5, 6], label="SMA 50")

    for series in (first, second):
        module.DearCyFiDemo._attach_legend_test_menu(host, series)

    def widgets(series):
        return [child for child in series.children if isinstance(child, dcg.uiItem)]

    first_identity, first_result, first_button = widgets(first)
    second_identity, second_result, second_button = widgets(second)
    assert first_identity.value == f"Series: SMA 20 (ID {first.uuid})"
    assert second_identity.value == f"Series: SMA 50 (ID {second.uuid})"
    assert first_result.value == second_result.value == "No action for this series yet."

    host._identify_legend_series(first_button, None, None)
    assert first_result.value == f"Legend action: Plot / SMA 20 (ID {first.uuid})"
    assert second_result.value == "No action for this series yet."
    host._identify_legend_series(second_button, None, None)
    assert second_result.value == f"Legend action: Plot / SMA 50 (ID {second.uuid})"
    assert messages[-1] == second_result.value

    with first.parent:
        added = PlotEconometricSeries(context, dates=[1, 2], values=[7, 8], label="SMA 100")
    module.DearCyFiDemo._attach_legend_test_menu(host, added)
    added_identity, added_result, _ = widgets(added)
    assert added_identity.value == f"Series: SMA 100 (ID {added.uuid})"
    assert added_result.value == "No action for this series yet."

    first.update_all(dates=[1, 2], values=[3, 4], label="Renamed")
    module.DearCyFiDemo._attach_legend_test_menu(host, first)
    assert widgets(first) == [first_identity, first_result, first_button]
    assert first_identity.value == f"Series: Renamed (ID {first.uuid})"
