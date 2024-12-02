from textual.app import ComposeResult
from textual.containers import HorizontalGroup

from tui.widgets.side import Side


class Keyboard(HorizontalGroup):
    def compose(self) -> ComposeResult:
        yield Side()
