import json
from itertools import cycle
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, PropertyMock, mock_open, patch

import pytest

if TYPE_CHECKING:
    from roki.firmware.calibration import Calibration


@pytest.fixture(autouse=True)
def max_iter(request):
    return getattr(request, "param", 1)


@pytest.fixture(autouse=True)
def button_values(request):
    return getattr(request, "param", [False])


@pytest.fixture
def mock_button(button_values: list[bool]):
    b = MagicMock()
    type(b).value = PropertyMock(side_effect=cycle(button_values))
    return b


@pytest.fixture
def mock_thumb_sticks():
    x = MagicMock()
    y = MagicMock()
    x.value = 0.0
    y.value = 0.0
    return x, y


@pytest.fixture
def calibration(
    mock_button: MagicMock,
    mock_thumb_sticks: tuple[MagicMock, MagicMock],
    max_iter: int,
):
    mock_thumb_stick_x, mock_thumb_stick_y = mock_thumb_sticks
    from roki.firmware.calibration import Calibration

    calibration = Calibration(
        mock_button,
        mock_thumb_stick_x,
        mock_thumb_stick_y,
        0.1,
        0.1,
        max_iterations=max_iter,
    )
    return calibration


@pytest.fixture(autouse=True)
def mock_blink_led():
    with patch("roki.firmware.calibration.blink_led") as m:
        m.return_value = None
        yield m


@pytest.fixture(autouse=True)
def mock_calibration_json():
    calibration_data = json.dumps(
        {
            "min_x": 0.0,
            "mid_x": 50.0,
            "max_x": 100.0,
            "min_y": 0.0,
            "mid_y": 50.0,
            "max_y": 100.0,
        }
    )
    with patch("builtins.open", mock_open(read_data=calibration_data)) as mock_file:
        yield mock_file


def test_calibration(
    calibration: "Calibration",
):
    with patch.object(
        calibration, "_write_config", wraps=calibration._write_config
    ) as m:
        calibration.start()
        m.assert_called()


@pytest.mark.parametrize("button_values", [[True]], indirect=True)
def test_calibration_skip_start(
    calibration: "Calibration",
):
    with patch.object(
        calibration, "_write_config", wraps=calibration._write_config
    ) as m:
        calibration.start()
        m.assert_not_called()


def test_calibration_readonly(
    calibration: "Calibration",
    mock_calibration_json: MagicMock,
):
    mock_calibration_json.side_effect = OSError("fake error")
    with patch.object(
        calibration, "_write_config", wraps=calibration._write_config
    ) as m:
        calibration.start()
        m.assert_called()


def test_calibration_read(calibration: "Calibration"):
    calibration.read()

    assert calibration.min_x != float("inf")
    assert calibration.max_x != -float("inf")
    assert calibration.min_y != float("inf")
    assert calibration.max_y != -float("inf")


def test_calibration_get_normalized(calibration: "Calibration"):
    x, y = calibration.get_normalized(15, 80)

    assert x < 0
    assert y > 0

    x, y = calibration.get_normalized(80, 15)

    assert x > 0
    assert y < 0

    assert calibration.get_normalized(51, 49) == (0, 0)
