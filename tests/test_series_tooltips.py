import dearcygui as dcg
import numpy as np
import pytest

from dearcyfi import PlotEconometricSeries
from dearcyfi.DCG_Candle_Utils import PlotCandleStick
from dearcyfi._series_tooltips import _DrawnHoverCondition


@pytest.fixture(params=["candle", "econometric"])
def series(request):
    context = dcg.Context()
    with dcg.Window(context):
        with dcg.Plot(context):
            if request.param == "candle":
                return PlotCandleStick(
                    context, dates=np.array([10, 20]), opens=np.array([2, 3]),
                    closes=np.array([3, 4]), lows=np.array([1, 2]),
                    highs=np.array([4, 5]), source_dates=np.array([100, 200]),
                )
            return PlotEconometricSeries(
                context, dates=[10, 20], values=[2, 3], source_dates=[100, 200],
            )


def _buttons(series):
    return [child for child in series.children if isinstance(child, dcg.DrawInvisibleButton)]


def test_tooltip_uses_shared_drawn_condition_and_preserves_hover_handlers(series):
    button = _buttons(series)[0]
    original_handlers = button.handlers
    series._tooltip_handler(None, button)

    condition = series._active_tooltip_condition
    tooltip = series._active_tooltip
    assert isinstance(condition, _DrawnHoverCondition)
    assert tooltip.condition_from_handler is condition
    assert tooltip.parent is series.parent.parent
    assert button.handlers == original_handlers + [condition]
    assert any(child.value.startswith("Date: ") for child in tooltip.children)
    assert button.user_data[0] == 100

    series._tooltip_handler(None, button)
    assert series._active_tooltip is tooltip
    assert button.handlers == original_handlers + [condition]

    series._tooltip_lost_handler(None, button)
    assert series._active_tooltip is None
    assert series._active_tooltip_condition is None
    assert button.handlers == original_handlers
    series._clear_active_tooltip()


def test_switching_and_rebuilding_tooltip_targets_removes_old_conditions(series):
    first, second = _buttons(series)
    original_handlers = first.handlers
    series._tooltip_handler(None, first)
    series._tooltip_handler(None, second)
    assert first.handlers == original_handlers
    assert series._active_tooltip_target is second

    series._tooltip_lost_handler(None, first)
    assert series._active_tooltip_target is second

    series.render()
    assert series._active_tooltip is None
    assert series._active_tooltip_target is None
    assert series._active_tooltip_condition is None
    assert not any(isinstance(handler, _DrawnHoverCondition) for handler in second.handlers)
    assert all(button is not first and button is not second for button in _buttons(series))


def test_redraw_preserves_legend_widgets_and_replaces_drawing_children(series):
    with series:
        menu_button = dcg.Button(series.context, label="Identify this series")
    old_buttons = _buttons(series)

    series.render()

    assert menu_button.parent is series
    assert menu_button in series.children
    assert all(button not in series.children for button in old_buttons)
    assert _buttons(series)
