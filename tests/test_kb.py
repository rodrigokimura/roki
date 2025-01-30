import pytest
from unittest.mock import patch, mock_open


@pytest.fixture(autouse=True)
def mock_config_json():
    with open("roki/firmware/config.json") as f:
        config = f.read()
    with patch("builtins.open", mock_open(read_data=config)) as mock_file:
        yield mock_file


@pytest.fixture(autouse=True)
def mock_init():
    with patch("roki.firmware.keys.init") as m:
        m.return_value = None
        yield m


def test_roki_subclasses_init():
    from roki.firmware.kb import Roki
    from roki.firmware.kb import Primary, Secondary

    rows = ("P0_24", "P1_00", "P0_11", "P1_04", "P1_06")
    cols = ("P0_09", "P0_10", "P1_11", "P1_13", "P1_15", "P0_02")
    encoder_pins = ("P0_17", "P0_20")
    thumb_stick_pins = ("P0_22", "AIN7", "AIN5")

    s = Secondary(rows, cols, thumb_stick_pins, encoder_pins)
    p = Primary(rows, cols, thumb_stick_pins, encoder_pins)

    assert isinstance(p, Roki)
    assert isinstance(s, Roki)
