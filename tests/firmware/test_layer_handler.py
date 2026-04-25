from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from roki.firmware.layer_handler import (
    Command,
    Commands,
    LayerHandler,
    OnHoldCommand,
    OnPressCommand,
    OnPressDecrementCommand,
    OnPressExtrasCommand,
    OnPressIncrementCommand,
)

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


def test_commands_containment(commands: Commands):
    assert "layer_1_hold" in commands
    assert "layer_99_hold" in commands
    assert "layer_1_press" in commands
    assert "layer_99_press" in commands
    assert "layer_inc" in commands
    assert "layer_dec" in commands
    assert "layer_extras" in commands


def test_commands_get(commands: Commands):
    result = commands.get("layer_2_hold")

    assert isinstance(result, Command)
    assert isinstance(result, OnHoldCommand)
    assert result.index == 2

    result = commands.get("layer_inc")

    assert isinstance(result, Command)
    assert isinstance(result, OnPressIncrementCommand)
    assert hasattr(result, "index") is False

    result = commands.get("layer_extras")

    assert isinstance(result, Command)
    assert isinstance(result, OnPressExtrasCommand)
    assert hasattr(result, "index") is False

    with pytest.raises(NotImplementedError):
        commands.get("layer_1_future_command")


def test_layer_handler_on_press_and_release_layer_1_press(layer_handler: LayerHandler):
    command = OnPressCommand(1)
    layer_handler.on_press(command)
    assert layer_handler.config.layer_index == 1
    layer_handler.on_release(command)
    assert layer_handler.config.layer_index == 1


def test_layer_handler_on_press_and_release_layer_inc_dec(layer_handler: LayerHandler):
    command = OnPressIncrementCommand(0)
    layer_handler.on_press(command)
    assert layer_handler.config.layer_index == 1
    layer_handler.on_release(command)
    assert layer_handler.config.layer_index == 1

    command = OnPressDecrementCommand(0)
    layer_handler.on_press(command)
    assert layer_handler.config.layer_index == 0
    layer_handler.on_release(command)
    assert layer_handler.config.layer_index == 0


def test_layer_handler_on_press_and_release_layer_1_hold(layer_handler: LayerHandler):
    command = OnHoldCommand(1)
    layer_handler.on_press(command)
    assert layer_handler.config.layer_index == 1
    layer_handler.on_release(command)
    assert layer_handler.config.layer_index == 0
