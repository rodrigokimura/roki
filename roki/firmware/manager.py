from __future__ import annotations

try:
    from typing import TYPE_CHECKING as __t

    TYPE_CHECKING = __t
except ImportError:  # pragma: no cover
    TYPE_CHECKING = False

if TYPE_CHECKING:  # pragma: no cover
    from .config import Config


class Manager:
    def __init__(self, config: Config) -> None:
        self._prev = 0
        self.config = config

    def on_press(self, command: Command) -> None:
        if command.press_or_hold:
            if command.index != self.config.layer_index:
                self._prev = self.config.layer_index
                self.config.layer_index = command.index
        else:
            if command.type_ == "inc":
                index = self.config.layer_index + 1
                max_layer = len(self.config.layers) - 1
                self.config.layer_index = min(index, max_layer)
            elif command.type_ == "dec":
                index = self.config.layer_index - 1
                self.config.layer_index = max(index, 0)

    def on_release(self, command: Command) -> None:
        if command.type_ == "hold":
            self.config.layer_index = self._prev


class Commands:
    def get(self, __name: str) -> Command:
        if __name.lower().startswith("layer_"):
            segments = __name.split("_")
            if len(segments) == 3:
                index = int(segments[1])
                type_ = segments[2]
            elif len(segments) == 2:
                _, type_ = segments
                index = 0
            else:
                raise NotImplementedError()
            return Command(int(index), type_)
        return Command()

    def __contains__(self, n: str) -> bool:
        return n.lower().startswith("layer_")


class Command:
    def __init__(self, index: int = 0, type_: str | None = None) -> None:
        self.index = index
        if not type_:
            self.type_ = None
        elif type_.lower() not in ("press", "hold", "inc", "dec"):
            self.type_ = None
        else:
            self.type_ = type_.lower()

    @property
    def press_or_hold(self):
        return self.type_ in ("press", "hold")
