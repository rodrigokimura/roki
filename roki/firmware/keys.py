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
    from typing import Callable, Literal, Sequence, TypeAlias

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
    from typing import Any

    from .config import Config

    Device: TypeAlias = Keyboard | Mouse | Media | LayerHandler
    Code: TypeAlias = KeyboardCode | MouseButton | MediaFunction | Commands
except ImportError:
    pass


sender_map: dict[Device, Code] = {}
sender_press: dict[Device, Callable] = {}
sender_release: dict[Device, Callable] = {}
sender_release_all: dict[Device, Callable] = {}
kb: Keyboard | None = None
mouse: Mouse | None = None
media: Media | None = None
lh: LayerHandler | None = None

hid: HIDService | None = None


def init(c: Config):
    global sender_map
    global sender_press
    global sender_release
    global sender_release_all
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

        sender_map = {
            kb: KeyboardCode(),
            mouse: MouseButton(),
            media: MediaFunction(),
            lh: Commands(),
        }
        sender_press = {
            kb: kb.press,
            mouse: mouse.press,
            media: media.press,
            lh: lh.on_press,
        }
        sender_release = {
            kb: kb.release,
            mouse: mouse.release,
            media: lambda _: media.release(),
            lh: lh.on_release,
        }
        sender_release_all = {
            kb: kb.release_all,
            mouse: mouse.release_all,
            media: media.release,
            lh: lh.on_release,
        }


class KeyWrapper:
    __slots__ = (
        "name",
        "sender",
        "key_code",
        "is_layer_handler",
    )

    name: str
    sender: Device | None
    key_code: int | DPad | Command
    is_layer_handler: bool

    def __init__(self, key: str | None = None) -> None:
        global sender_map
        key = key or "noop"

        from roki.firmware.params import Params

        if Params().DEBUG:
            self.name = key

        self.sender = None
        self.key_code = 0
        for sender, key_container in sender_map.items():
            if key in key_container:
                self.sender = sender
                self.key_code = key_container.get(key)

        self.is_layer_handler = isinstance(self.sender, LayerHandler)

    def _release(self, sender: Device, key_code: Any) -> None:
        sender_release[sender](key_code)

    def press(self) -> None:
        if self.sender:
            sender_press[self.sender](self.key_code)

    def release(self) -> None:
        if self.is_layer_handler:
            self.release_all()
        elif self.sender:
            sender_release[self.sender](self.key_code)

    def release_all(self) -> None:
        if self.sender:
            sender_release_all[self.sender](self.key_code)

    def press_and_release(self) -> None:
        self.press()
        self.release()


if Params().DEBUG:

    class KeyWrapper(KeyWrapper):
        def press(self):
            logger.debug("Keys: " + str(self.name) + " Event: PRESS")
            super().press()

        def release(self):
            logger.debug("Keys: " + str(self.name) + " Event: RELEASE")
            super().release()
