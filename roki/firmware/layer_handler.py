from __future__ import annotations

try:
    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from .config import Config
except Exception:
    pass


class LayerHandler:
    __slots__ = (
        "_prev",
        "config",
    )

    _prev: int
    config: Config

    def __init__(self, config: Config) -> None:
        self._prev = 0
        self.config = config

    def on_press(self, command: Command) -> None:
        command.press(self)

    def on_release(self, command: Command) -> None:
        command.release(self)


class Commands:
    __slots__ = tuple()

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

            command_classes: dict[str, type[Command]] = {
                "press": OnPressCommand,
                "hold": OnHoldCommand,
                "inc": OnPressIncrementCommand,
                "dec": OnPressDecrementCommand,
                "extras": OnPressExtrasCommand,
            }
            return command_classes[type_.lower()](int(index))

        return Command(0)

    def __contains__(self, n: str) -> bool:
        return n.lower().startswith("layer_")


class Command:
    __slots__ = ("index",)

    index: int

    def __init__(self, index: int = 0):
        pass

    def press(self, lh: LayerHandler):
        raise NotImplementedError

    def release(self, lh: LayerHandler):
        raise NotImplementedError


class OnPressCommand(Command):
    def __init__(self, index: int):
        self.index = index

    def press(self, lh: LayerHandler):
        if self.index != lh.config.layer_index:
            lh._prev = lh.config.layer_index
            lh.config.layer_index = self.index

    def release(self, lh: LayerHandler):
        pass


class OnPressIncrementCommand(OnPressCommand):
    def __init__(self, index: int = 0):
        pass

    def press(self, lh: LayerHandler):
        index = lh.config.layer_index + 1
        max_layer = len(lh.config.layers) - 1
        lh.config.layer_index = min(index, max_layer)


class OnPressDecrementCommand(OnPressCommand):
    def __init__(self, index: int = 0):
        pass

    def press(self, lh: LayerHandler):
        index = lh.config.layer_index - 1
        lh.config.layer_index = max(index, 0)


class OnHoldCommand(OnPressCommand):
    def release(self, lh: LayerHandler):
        lh.config.layer_index = lh._prev


class OnPressExtrasCommand(OnPressCommand):
    def __init__(self, index: int = 0):
        pass

    def press(self, lh: LayerHandler):
        lh.config.extras = not lh.config.extras
