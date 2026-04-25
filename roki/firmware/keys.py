from __future__ import annotations

import usb_hid
from adafruit_ble.services.standard.hid import HIDService
from adafruit_hid.consumer_control import ConsumerControl as Media
from adafruit_hid.consumer_control_code import ConsumerControlCode as MediaKey
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
from adafruit_hid.mouse import Mouse as _Mouse

from roki.firmware import logging
from roki.firmware.layer_handler import Command, Commands, LayerHandler
from roki.firmware.params import Params

try:
    from typing import Literal, Sequence, Type, TypeAlias

    DPad = Literal["u", "d", "l", "r", "su", "sd"]
except ImportError:
    pass

logger = logging.getLogger(__name__)


class Mouse(_Mouse):
    def __init__(
        self,
        devices: Sequence[usb_hid.Device],
        timeout: int = 2,
        mouse_movement: int = 20,
        mouse_scroll: int = 2,
    ) -> None:
        self.mouse_movement = mouse_movement
        self.mouse_scroll = mouse_scroll
        super().__init__(devices, timeout)

    def press(self, buttons: int | DPad) -> None:
        if isinstance(buttons, str):
            if buttons == "u":
                self.move(y=-self.mouse_movement)
            elif buttons == "d":
                self.move(y=self.mouse_movement)
            elif buttons == "l":
                self.move(x=-self.mouse_movement)
            elif buttons == "r":
                self.move(x=self.mouse_movement)
            elif buttons == "su":
                self.move(wheel=self.mouse_scroll)
            elif buttons == "sd":
                self.move(wheel=-self.mouse_scroll)
        else:
            return super().press(buttons)

    def release(self, buttons: int | DPad) -> None:
        if isinstance(buttons, int):
            return super().release(buttons)


class KeyboardCode:
    def get(self, n: str) -> int:
        return getattr(Keycode, n)

    def __contains__(self, n: str) -> bool:
        return hasattr(Keycode, n)


class MouseButton:
    movement: dict[str, DPad] = {
        "MOUSE_MOVE_UP": "u",
        "MOUSE_MOVE_DOWN": "d",
        "MOUSE_MOVE_LEFT": "l",
        "MOUSE_MOVE_RIGHT": "r",
        "MOUSE_SCROLL_UP": "su",
        "MOUSE_SCROLL_DOWN": "sd",
    }

    def get(self, n: str) -> int | DPad:
        if hasattr(Mouse, n):
            return getattr(Mouse, n)
        return self.movement[n]

    def __contains__(self, n: str) -> bool:
        return hasattr(Mouse, n) or (n in self.movement)


class MediaFunction:
    def get(self, n: str) -> int:
        return getattr(MediaKey, n)

    def __contains__(self, n: str) -> bool:
        return hasattr(MediaKey, n)


try:
    from .config import Config

    Device: TypeAlias = Keyboard | Mouse | Media | LayerHandler
    Code: TypeAlias = KeyboardCode | MouseButton | MediaFunction | Commands
except ImportError:
    pass


kb: Keyboard = None  # type: ignore lazy initialization
mouse: Mouse = None  # type: ignore lazy initialization
media: Media = None  # type: ignore lazy initialization
lh: LayerHandler = None  # type: ignore lazy initialization


hid: HIDService | None = None


class BaseKey:
    key_code: int | DPad | Command

    __slots__ = ("key_code",)

    @classmethod
    def build(cls, key: str | None) -> BaseKey:
        if not key:
            return NoopKey()

        sender_map: tuple[tuple[Code, Type[BaseKey]], ...] = (
            (KeyboardCode(), KeyboardKey),
            (MouseButton(), MouseKey),
            (MediaFunction(), MultiMediaKey),
            (Commands(), LayerHandlerKey),
        )

        for code, key_class in sender_map:
            if key in code:
                key_code = code.get(key)

                return key_class(key_code)

        return NoopKey()

    def __init__(self, key_code: int | DPad | Command):
        self.key_code = key_code

    def press(self) -> None:
        raise NotImplementedError()

    def release(self) -> None:
        raise NotImplementedError()


class NoopKey(BaseKey):
    def __init__(self):
        pass

    def press(self):
        pass

    def release(self):
        pass


class MouseKey(BaseKey):
    key_code: int | DPad

    def press(self):
        global mouse
        mouse.press(self.key_code)

    def release(self):
        global mouse
        mouse.press(self.key_code)


class KeyboardKey(BaseKey):
    key_code: int

    def press(self):
        global kb
        kb.press(self.key_code)

    def release(self):
        global kb
        kb.release(self.key_code)


class MultiMediaKey(BaseKey):
    key_code: int

    def press(self):
        global media
        media.press(self.key_code)

    def release(self):
        global media
        media.release()


class LayerHandlerKey(BaseKey):
    key_code: Command

    def press(self):
        global lh
        global kb
        kb.release_all()
        lh.on_press(self.key_code)

    def release(self):
        global lh
        global kb
        kb.release_all()
        lh.on_release(self.key_code)


def init(c: Config):
    global kb
    global mouse
    global media
    global lh
    global hid

    if hid is None:
        hid = HIDService()
        kb = Keyboard(hid.devices)
        mouse = Mouse(hid.devices)
        media = Media(hid.devices)
        lh = LayerHandler(c)


if Params().DEBUG:
    pass
