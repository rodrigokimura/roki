from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def mock_init():
    with patch("roki.firmware.keys.init") as m:
        m.return_value = None
        yield m


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
