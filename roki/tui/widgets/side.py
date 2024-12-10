from textual.app import ComposeResult
from textual.containers import HorizontalGroup, VerticalGroup

from tui.widgets.key import Key


class Side(VerticalGroup):
    def compose(self) -> ComposeResult:
        with HorizontalGroup():
            for col in range(6):
                yield Column(index=col)

        with HorizontalGroup():
            for col in range(6):
                yield Key(id=f"key_5_{col}", label="0")


class Column(VerticalGroup):
    DEFAULT_CSS = """
    Column {
        width: auto;
    }
    """

    def __init__(
        self,
        index: int,
        name: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        self.index = index
        super().__init__(
            name=name, id=f"col_{index}", classes=classes, disabled=disabled
        )

    def compose(self) -> ComposeResult:
        for row in range(4):
            yield Key(id=f"key_{row}_{self.index}", label="0")
