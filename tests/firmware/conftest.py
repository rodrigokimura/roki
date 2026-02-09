from unittest.mock import MagicMock, mock_open, patch

import pytest


@pytest.fixture(autouse=True)
def mock_config_json():
    with open("roki/firmware/config.json") as f:
        config = f.read()
    with patch("builtins.open", mock_open(read_data=config)) as mock_file:
        yield mock_file


@pytest.fixture
def mock_find_device():
    with (
        patch("adafruit_hid.keyboard.find_device") as m_keyboard,
        patch("adafruit_hid.mouse.find_device") as m_mouse,
        patch("adafruit_hid.consumer_control.find_device") as m_media,
    ):
        yield m_keyboard, m_mouse, m_media


@pytest.fixture
def mock_hid_service(mock_find_device: tuple[MagicMock, MagicMock, MagicMock]):
    mm = MagicMock()
    mm.devices = []
    with patch("roki.firmware.keys.HIDService") as m:
        m.return_value = mm
        yield m
