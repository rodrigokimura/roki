from __future__ import annotations

import usb_hid
from adafruit_ble.services.standard.hid import HIDService
from adafruit_hid.consumer_control import ConsumerControl as Media
from adafruit_hid.consumer_control_code import ConsumerControlCode as MediaKey
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
from adafruit_hid.mouse import Mouse as _Mouse

from roki.firmware.layer_handler import Commands, LayerHandler
from roki.firmware.utils import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from typing import Literal, Sequence, TypeAlias

    DPad = Literal["u", "d", "l", "r", "su", "sd"]


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


if TYPE_CHECKING:  # pragma: no cover
    from typing import Any

    from .config import Config

    Device: TypeAlias = Keyboard | Mouse | Media | LayerHandler
    Code: TypeAlias = KeyboardCode | MouseButton | MediaFunction | Commands


sender_map: dict[Device, Code] = {}
kb: Keyboard | None = None
mouse: Mouse | None = None
media: Media | None = None

HID: HIDService | None = None


def init(c: Config):
    global sender_map
    global kb
    global mouse
    global media
    global HID

    if HID is None:
        HID = HIDService()
        kb = Keyboard(HID.devices)
        mouse = Mouse(HID.devices)
        media = Media(HID.devices)

        sender_map = {
            kb: KeyboardCode(),
            mouse: MouseButton(),
            media: MediaFunction(),
            LayerHandler(c): Commands(),
        }


class KeyWrapper:
    def __init__(self, keys: str | list[str] | None = None) -> None:
        global sender_map
        keys = keys or "noop"
        if isinstance(keys, str):
            keys = [keys.upper()]
        else:
            keys = [key.upper() for key in keys]

        self.params = tuple(
            (sender, key_container.get(key))
            for sender, key_container in sender_map.items()
            for key in keys
            if key in key_container
        )
        self.is_layer_handler = any(isinstance(s, LayerHandler) for s, _ in self.params)

    def _press(self, sender: Device, key_code: Any) -> None:
        if isinstance(sender, Media):
            sender.press(key_code)
        elif isinstance(sender, Keyboard):
            sender.press(key_code)
        elif isinstance(sender, Mouse):
            sender.press(key_code)
        elif isinstance(sender, LayerHandler):
            sender.on_press(key_code)

    def _release(self, sender: Device, key_code: Any) -> None:
        if isinstance(sender, Media):
            sender.release()
        elif isinstance(sender, Keyboard):
            sender.release(key_code)
        elif isinstance(sender, Mouse):
            sender.release(key_code)
        elif isinstance(sender, LayerHandler):
            sender.on_release(key_code)

    def press(self) -> None:
        for sender, key_code in self.params:
            self._press(sender, key_code)

    def release(self) -> None:
        for sender, key_code in self.params:
            self._release(sender, key_code)
        if self.is_layer_handler:
            self.release_all()

    def release_all(self) -> None:
        if kb:
            kb.release_all()
        if mouse:
            mouse.release_all()
        if media:
            media.release()

    def press_and_release(self) -> None:
        self.press()
        self.release()
