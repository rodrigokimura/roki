from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from roki.firmware.keys import Mouse


@pytest.fixture
def mock_find_device():
    with (
        patch("adafruit_hid.keyboard.find_device") as m_keyboard,
        patch("adafruit_hid.mouse.find_device") as m_mouse,
        patch("adafruit_hid.consumer_control.find_device") as m_media,
    ):
        yield m_keyboard, m_mouse, m_media


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


@pytest.fixture
def mock_hid_service(mock_find_device: tuple[MagicMock, MagicMock, MagicMock]):
    mm = MagicMock()
    mm.devices = []
    with patch("roki.firmware.keys.HIDService") as m:
        m.return_value = mm
        yield m
        assert sum(m.call_count for m in mock_find_device) > 0


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

    kw = KeyWrapper(["Z", "MUTE", "LEFT_BUTTON", "LAYER_0_PRESS"])
    kw.press_and_release()

    mock_hid_service.assert_called()
