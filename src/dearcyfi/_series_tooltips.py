import dearcygui as dcg


class _DrawnHoverCondition(dcg.CustomHandler):
    """Require a drawn target as well as hover, ignoring hidden stale state.

    Legend-hidden DrawInPlot children are skipped without updating hover.
    The button records drawing in run(); the tooltip consumes that record.
    """

    def __init__(self, context, **kwargs) -> None:
        super().__init__(context, **kwargs)
        self._drawn = False

    def check_can_bind(self, item) -> bool:
        return isinstance(item, dcg.DrawInvisibleButton)

    def check_status(self, item) -> bool:
        drawn, self._drawn = self._drawn, False
        return drawn and item.state.hovered

    def run(self, item) -> None:
        self._drawn = True
