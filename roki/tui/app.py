from textual import on
from textual.app import App, ComposeResult
from textual.widgets import Footer, Header

from roki.tui.screens.key_editor import KeyEditor
from roki.tui.widgets.key import Key
from roki.tui.widgets.keyboard import Keyboard


class Configurator(App):
    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("q", "exit", "Exit app"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Keyboard()
        yield Footer()

    def action_exit(self) -> None:
        self.exit(message="Exiting app")

    @on(Key.Pressed)
    def handle_key_press(self, event: Key.Pressed):
        if isinstance(event.control, Key):
            self.app.notify(str(event.control.id))
            self.push_screen(KeyEditor())
