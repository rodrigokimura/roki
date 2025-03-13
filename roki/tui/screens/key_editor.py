from textual import on
from textual import events
from textual.app import ComposeResult
from textual.containers import HorizontalGroup, VerticalGroup
from textual.screen import Screen
from textual.widgets import Button, Input, ListItem, ListView, Label, Select


from roki.cli.config.keys import KEYS


class KeyEditor(Screen):
    DEFAULT_CSS = """
    KeyEditor {
        align: center middle;
    }
    #container {
        border: round $background 80%;
        width: 100;
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
    ListView {
        width: 100%;
        height: 20;
        overflow-y: scroll;
    }
    """

    def compose(self) -> ComposeResult:
        options = [(k.name, k.description) for k in KEYS]
        self.keys = Input(disabled=True)
        self.search = Input(id="search")
        self.options = ListView()
        self.options.shrink = True
        self.options.expand = True
        self.input = Select(options, classes="key")
        self.search._initialize_data_bind

        with VerticalGroup(id="container"):
            with HorizontalGroup():
                yield self.search
                yield self.input
                yield Button("OK", id="confirm")
            with HorizontalGroup():
                yield self.options
                yield self.keys
            with HorizontalGroup():
                yield Button("Cancel", id="cancel")
                yield Button("OK", id="ok")

    def on_mount(self):
        # self.options.add_options((Option(k.name, id=k.name) for k in KEYS))
        pass

    @on(Input.Changed, "#search")
    def search_text(self, msg: Input.Changed):
        text = msg.value
        self.options.clear()
        self.options.extend(
            (ListItem(Label(k.name)) for k in KEYS if text in k.description)
        )

    @on(Button.Pressed)
    def handle_button_press(self, event: Button.Pressed):
        if event.control.id == "cancel":
            self.app.pop_screen()
        if event.control.id == "confirm":
            self.keys.value = self.input.value

    async def on_event(self, event: events.Event) -> None:
        if isinstance(event, events.Key):
            if event.key == "up":
                pass
                self.options.index
            # self.post_message()
            self.app.notify(event.key)
        return await super().on_event(event)
