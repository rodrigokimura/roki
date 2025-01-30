import json
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, mock_open, patch

import pytest

if TYPE_CHECKING:
    from roki.firmware.calibration import Calibration


@pytest.fixture
def mock_button():
    m = MagicMock()
    m.value = False
    return m


@pytest.fixture
def mock_thumb_sticks():
    x = MagicMock()
    y = MagicMock()
    x.value = 0.0
    y.value = 0.0
    return x, y


@pytest.fixture
def calibration(mock_button: MagicMock, mock_thumb_sticks: tuple[MagicMock, MagicMock]):
    from roki.firmware.calibration import Calibration

    mock_thumb_stick_x, mock_thumb_stick_y = mock_thumb_sticks
    return Calibration(
        mock_button,
        mock_thumb_stick_x,
        mock_thumb_stick_y,
        0.1,
        0.1,
        max_iterations=1,
    )


@pytest.fixture
def mock_blink_led():
    with patch("roki.firmware.calibration.blink_led") as m:
        m.return_value = None
        yield m


@pytest.fixture(autouse=True)
def mock_calibration_json():
    calibration_data = json.dumps(
        {
            "min_x": 0.0,
            "mid_x": 0.0,
            "max_x": 0.0,
            "min_y": 0.0,
            "mid_y": 0.0,
            "max_y": 0.0,
        }
    )
    with patch("builtins.open", mock_open(read_data=calibration_data)) as mock_file:
        yield mock_file


def test_calibration(
    calibration: "Calibration",
    mock_blink_led: MagicMock,
):
    calibration.start()
    mock_blink_led.assert_called()


def test_calibration_read(calibration: "Calibration"):
    calibration.read()
