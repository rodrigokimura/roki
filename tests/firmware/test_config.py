from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def mock_init():
    with patch("roki.firmware.keys.init") as m:
        m.return_value = None
        yield m


@pytest.fixture()
def layer_dict():
    return {
        "name": "main",
        "color": "#3584e4",
        "primary_keys": [
            ["ESCAPE", "ONE", "TWO", "THREE", "FOUR", "FIVE"],
            ["TAB", "Q", "W", "E", "R", "T"],
            ["LEFT_SHIFT", "A", "S", "D", "F", "G"],
            ["LAYER_1_HOLD", "Z", "X", "C", "V", "B"],
            [
                "LEFT_CONTROL",
                "LEFT_GUI",
                "LEFT_ALT",
                "SPACEBAR",
                "ENTER",
                "CAPS_LOCK",
            ],
        ],
        "secondary_keys": [
            ["SIX", "SEVEN", "EIGHT", "NINE", "ZERO", "LAYER_EXTRAS"],
            ["Y", "U", "I", "O", "P", "GRAVE_ACCENT"],
            ["H", "J", "K", "L", "FORWARD_SLASH", "RIGHT_SHIFT"],
            ["N", "M", "COMMA", "PERIOD", "KEYPAD_BACKSLASH", "LAYER_1_HOLD"],
            [
                "ESCAPE",
                "BACKSPACE",
                "SPACEBAR",
                "RIGHT_ALT",
                "RIGHT_GUI",
                "RIGHT_CONTROL",
            ],
        ],
        "primary_encoder": ["VOLUME_INCREMENT", "VOLUME_DECREMENT"],
        "secondary_encoder": ["UP_ARROW", "DOWN_ARROW"],
    }


@pytest.mark.parametrize(
    "input",
    [
        "ffffff",
        (255, 255, 255),
        (255, 255, 255, 111),
        [255, 255, 255],
        [255, 255, 255, 111],
    ],
)
def test_parse_color(input):
    from roki.firmware.config import parse_color

    color = parse_color(input)

    assert color == (255, 255, 255)


def test_parse_color_invalid():
    from roki.firmware.config import parse_color

    with pytest.raises(ValueError):
        parse_color("ffffffffffff")


def test_layer_from_dict(layer_dict: dict):
    from roki.firmware.config import Layer

    layer = Layer.from_dict(layer_dict)

    assert isinstance(layer, Layer)

    print(layer)
