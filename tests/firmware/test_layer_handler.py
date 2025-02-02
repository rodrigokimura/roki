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

    return Config.read()


@pytest.fixture
def layer_handler(config: "Config"):
    return LayerHandler(config)


@pytest.fixture
def command():
    return Command()


@pytest.fixture
def commands():
    return Commands()


def test_invalis_command():
    c = Command(type_="invalid")
    assert c.type_ is None


def test_commands_containment(commands: Commands):
    assert "layer_1_hold" in commands


def test_commands_get(commands: Commands):
    result = commands.get("layer_2_hold")
    assert isinstance(result, Command)
    assert result.index == 2
    assert result.type_ == "hold"
    result = commands.get("layer_inc")
    assert isinstance(result, Command)
    assert result.index == 0
    assert result.type_ == "inc"
    result = commands.get("invalid")
    assert isinstance(result, Command)
    assert result.index == 0
    assert result.type_ is None
    with pytest.raises(NotImplementedError):
        commands.get("layer_1_future_command")


def test_layer_handler_on_press_and_release_layer_1_press(layer_handler: LayerHandler):
    command = Command(1, "press")
    layer_handler.on_press(command)
    assert layer_handler.config.layer_index == 1
    layer_handler.on_release(command)
    assert layer_handler.config.layer_index == 1


def test_layer_handler_on_press_and_release_layer_inc_dec(layer_handler: LayerHandler):
    command = Command(0, "inc")
    layer_handler.on_press(command)
    assert layer_handler.config.layer_index == 1
    layer_handler.on_release(command)
    assert layer_handler.config.layer_index == 1

    command = Command(0, "dec")
    layer_handler.on_press(command)
    assert layer_handler.config.layer_index == 0
    layer_handler.on_release(command)
    assert layer_handler.config.layer_index == 0


def test_layer_handler_on_press_and_release_layer_1_hold(layer_handler: LayerHandler):
    layer_handler.on_press(Command(1, "hold"))
    assert layer_handler.config.layer_index == 1
    layer_handler.on_release(Command(1, "hold"))
    assert layer_handler.config.layer_index == 0
