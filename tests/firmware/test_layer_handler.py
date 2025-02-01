from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from roki.firmware.layer_handler import Command, Commands, LayerHandler

if TYPE_CHECKING:
    from roki.firmware.config import Config


@pytest.fixture(autouse=True)
def mock_init():
    with patch("roki.firmware.keys.init") as m:
        m.return_value = None
        yield m


@pytest.fixture
def config():
    from roki.firmware.config import Config

    return Config()


@pytest.fixture
def layer_handler(config: "Config"):
    return LayerHandler(config)


@pytest.fixture
def command():
    return Command()


@pytest.fixture
def commands():
    return Commands()


def test_commands_containment(commands: Commands):
    assert "layer_2" in commands


def test_commands_get(commands: Commands):
    result = commands.get("layer_2_hold")
    assert isinstance(result, Command)
    assert result.index == 2
    assert result.type_ == "hold"


def test_layer_handler(layer_handler: LayerHandler, command: Command):
    layer_handler.on_press(command)
