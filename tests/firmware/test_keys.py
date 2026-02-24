from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from roki.firmware.keys import Mouse


@pytest.fixture
def mouse(mock_find_device: tuple[MagicMock, MagicMock, MagicMock]):
    from roki.firmware.keys import Mouse

    _, m, _ = mock_find_device

    mouse = Mouse([])
    m.assert_called()
    return mouse


@pytest.fixture
def wrap_mouse_move(mouse: "Mouse"):
    with patch.object(mouse, "move", wraps=mouse.move) as m:
        yield m


def test_mouse(mouse: "Mouse", wrap_mouse_move: MagicMock):
    mouse.press("u")
    wrap_mouse_move.assert_called_with(y=-20)
    mouse.press("d")
    wrap_mouse_move.assert_called_with(y=20)
    mouse.press("l")
    wrap_mouse_move.assert_called_with(x=-20)
    mouse.press("r")
    wrap_mouse_move.assert_called_with(x=20)
    mouse.press("su")
    wrap_mouse_move.assert_called_with(wheel=2)
    mouse.press("sd")
    wrap_mouse_move.assert_called_with(wheel=-2)
    mouse.press(1)
    mouse.release(1)


def test_mouse_button():
    from roki.firmware.keys import MouseButton

    assert "MOUSE_MOVE_UP" in MouseButton()
    assert "LEFT_BUTTON" in MouseButton()
    assert MouseButton().get("MOUSE_MOVE_UP") == "u"
    assert MouseButton().get("LEFT_BUTTON") == 1


def test_keyboard_code():
    from roki.firmware.keys import KeyboardCode

    assert "A" in KeyboardCode()
    assert KeyboardCode().get("A") == 0x04


def test_media_function():
    from roki.firmware.keys import MediaFunction

    assert "MUTE" in MediaFunction()
    assert MediaFunction().get("MUTE") == 0xE2


def test_key_wrapper(mock_hid_service: MagicMock):
    from roki.firmware.config import Config
    from roki.firmware.keys import KeyWrapper, init

    init(Config())

    for k in (
        "Z",
        "MUTE",
        "LEFT_BUTTON",
        "LAYER_0_PRESS",
    ):
        kw = KeyWrapper(k)
        kw.press_and_release()
