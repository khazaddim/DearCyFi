import asyncio
import importlib.util
from pathlib import Path
from types import MethodType, SimpleNamespace

import dearcygui as dcg
import pytest

from dearcyfi import DearCyFi, PlotEconometricSeries


@pytest.fixture
def demo_class(monkeypatch):
    demo_dir = Path(__file__).parents[1] / "examples" / "DearCyFi_Demo"
    monkeypatch.syspath_prepend(str(demo_dir))
    monkeypatch.setattr(asyncio, "set_event_loop", lambda loop: None)
    spec = importlib.util.spec_from_file_location("dearcyfi_demo_legend_test", demo_dir / "DearCyFi_Demo.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.loop.close()
    return module.DearCyFiDemo


def test_legend_menus_identify_each_series_independently(demo_class):
    context = dcg.Context()
    messages = []
    host = SimpleNamespace(C=context, _legend_test_series={}, set_status=messages.append)
    host._identify_legend_series = MethodType(demo_class._identify_legend_series, host)
    with dcg.Window(context):
        with dcg.Plot(context, label="Plot"):
            first = PlotEconometricSeries(context, dates=[1, 2], values=[3, 4], label="SMA 20")
            second = PlotEconometricSeries(context, dates=[1, 2], values=[5, 6], label="SMA 50")

    for series in (first, second):
        demo_class._attach_legend_test_menu(host, series)

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
    demo_class._attach_legend_test_menu(host, added)
    added_identity, added_result, _ = widgets(added)
    assert added_identity.value == f"Series: SMA 100 (ID {added.uuid})"
    assert added_result.value == "No action for this series yet."

    first.update_all(dates=[1, 2], values=[3, 4], label="Renamed")
    demo_class._attach_legend_test_menu(host, first)
    assert widgets(first) == [first_identity, first_result, first_button]
    assert first_identity.value == f"Series: Renamed (ID {first.uuid})"


def test_sma_buttons_act_on_the_selected_indicator(demo_class, capsys):
    demo = demo_class.__new__(demo_class)
    demo.C = dcg.Context()
    demo._legend_test_series = {}
    demo._indicator_edit_popups = {}
    messages = []
    demo.set_status = messages.append

    with dcg.Window(demo.C):
        demo.DCF_plot = DearCyFi(demo.C, prewarm=False)
        demo.indicator_period_slider = dcg.Slider(demo.C, value=2, min_value=1, max_value=500)
        demo.indicator_field_radio = dcg.RadioButton(demo.C, items=["Close"], value="Close")
        demo.indicator_line_color_edit = dcg.ColorEdit(demo.C, value=(255, 196, 0, 255))
        demo.indicator_status = dcg.Text(demo.C)
        add = dcg.Button(demo.C, callback=demo._add_sma_indicator)
    demo.DCF_plot.set_data(
        dates=[0.0, 300.0, 600.0, 900.0],
        opens=[1.0, 2.0, 3.0, 4.0],
        highs=[2.0, 3.0, 4.0, 5.0],
        lows=[0.0, 1.0, 2.0, 3.0],
        closes=[1.0, 2.0, 3.0, 4.0],
    )

    def click(button):
        button.callback[0](button, button, button.value)

    def button_in(parent, label):
        return next(child for child in parent.children if isinstance(child, dcg.Button) and child.label == label)

    click(add)
    click(add)
    first_id, second_id = demo.DCF_plot.indicator_ids
    manager = demo.DCF_plot.indicator_manager
    first, second = manager.get(first_id), manager.get(second_id)
    assert first.series.line_color == (255, 196, 0, 255)
    demo.indicator_line_color_edit.value = dcg.color_as_int((30, 60, 90, 255))
    click(add)
    third_id = demo.DCF_plot.indicator_ids[-1]
    third = manager.get(third_id)
    assert third.series.line_color == (30, 60, 90, 255)

    edit = button_in(second.series, "Edit indicator")
    click(edit)
    popup = demo._indicator_edit_popups[second_id]
    click(edit)
    assert demo._indicator_edit_popups == {second_id: popup}
    assert "raised exception" not in capsys.readouterr().out
    slider = next(child for child in popup.children if isinstance(child, dcg.Slider))
    color_edit = next(child for child in popup.children if isinstance(child, dcg.ColorEdit))
    assert dcg.color_as_ints(color_edit.value) == second.series.line_color
    slider.value = 3
    color_edit.value = dcg.color_as_int((40, 70, 100, 255))
    click(button_in(popup, "Apply"))
    assert not demo._indicator_edit_popups
    assert manager.get(second_id).calculator.period == 3
    assert manager.get(second_id).series.line_color == (40, 70, 100, 255)
    assert manager.get(first_id).calculator.period == 2

    click(edit)
    popup = demo._indicator_edit_popups[second_id]
    click(button_in(popup, "Cancel"))
    assert not demo._indicator_edit_popups
    assert messages[-1] == "Indicator edit canceled."

    click(edit)
    click(button_in(second.series, "Remove indicator"))
    assert not demo._indicator_edit_popups
    assert demo.DCF_plot.indicator_ids == (first_id, third_id)
    assert second.registration_id not in demo.DCF_plot.time_series_ids
    assert first.registration_id in demo.DCF_plot.time_series_ids
    assert third.registration_id in demo.DCF_plot.time_series_ids
    assert second.series not in demo.DCF_plot.children
    assert second.series.uuid not in demo._legend_test_series
