from textual.app import App, ComposeResult
from textual.widgets import Footer, Header

from tui.widgets.keyboard import Keyboard


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
