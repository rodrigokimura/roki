from textual import on
from roki.cli.config.keys import KEYS
from textual.app import ComposeResult
from textual.containers import HorizontalGroup, VerticalGroup
from textual.screen import ModalScreen
from textual.suggester import SuggestFromList
from textual.widgets import Button, Input, OptionList, Select


class KeyEditor(ModalScreen):
    DEFAULT_CSS = """
    KeyEditor {
        align: center middle;
    }
    #container {
        border: round $background 80%;
        width: 100;
        height: 20;
    }
    Input.key {
        width: 3fr;
    }
    Button#confirm {
        width: 1fr;
    }
    #ok, #cancel {
        width: 1fr;
        margin: 1;
    }
    """

    def compose(self) -> ComposeResult:
        options = [(k.name, k.description) for k in KEYS]
        self.keys = Input(disabled=True)
        self.search = Input(id="search")
        self.options = OptionList()
        self.input = Select(
            options,
            classes="key",
            # suggester=SuggestFromList(options, case_sensitive=False),
        )
        with VerticalGroup(id="container"):
            with HorizontalGroup():
                yield self.search
                yield self.input
                yield Button("OK", id="confirm")
            with HorizontalGroup():
                yield self.keys
            with HorizontalGroup():
                yield Button("Cancel", id="cancel")
                yield Button("OK", id="ok")

    @on(Input.Changed, "#search")
    def search_text(self):
        self

    @on(Button.Pressed)
    def handle_button_press(self, event: Button.Pressed):
        if event.control.id == "cancel":
            self.app.pop_screen()
        if event.control.id == "confirm":
            self.keys.value = self.input.value
