import json
from unittest.mock import MagicMock, patch

import pytest

from roki.cli.utils import (
    create_mount_point,
    get_serial_device,
    install_circuitpython_libs,
    unmount,
)


@pytest.fixture
def mock_subprocess():
    with patch("subprocess.check_output") as m:
        output = {
            "blockdevices": [
                {
                    "model": "nice!nano",
                    "vendor": "Nice Key",
                    "children": [
                        {
                            "label": "CIRCUITPY",
                            "name": "sda1",
                        }
                    ],
                },
            ]
        }
        m.return_value = json.dumps(output)
        yield m


@pytest.fixture
def mock_subprocess_call():
    with patch("subprocess.call") as m:
        m.return_value = None
        yield m


@pytest.fixture
def mock_run_command():
    with patch("roki.cli.utils.run_command") as m:
        yield m


def test_get_devices(mock_subprocess: MagicMock):
    from roki.cli.utils import get_devices

    result = get_devices()

    assert result == ["sda1"]
    mock_subprocess.assert_called_once()


def test_run_command(mock_subprocess_call: MagicMock):
    from roki.cli.utils import run_command

    run_command("dummy")

    mock_subprocess_call.assert_called_once_with(["dummy"], umask=0)


def test_run_command_as_sudo(mock_subprocess_call: MagicMock):
    from roki.cli.utils import run_command

    run_command("dummy", shell=True)

    mock_subprocess_call.assert_called_once_with("dummy", shell=True, umask=0)


def test_install_circuitpython_libs(mock_run_command: MagicMock):
    install_circuitpython_libs("dummy/path", "dummy_file.py")

    mock_run_command.assert_called_once_with(
        "circup --path dummy/path install --auto-file dummy_file.py"
    )


def test_create_mount_point(mock_run_command: MagicMock):
    create_mount_point("dummy_device", "dummy/path")

    mock_run_command.assert_called_once_with(
        "sudo mount -o uid=1000,gid=1000 /dev/dummy_device dummy/path"
    )


def test_unmount(mock_run_command: MagicMock):
    unmount("dummy/path")

    mock_run_command.assert_called_once_with("sudo umount dummy/path")


def test_get_serial_device(mock_subprocess: MagicMock):
    mock_subprocess.return_value = b"Nice Keyboards, CircuitPython CDC control@sda1"
    result = get_serial_device()

    assert result == "sda1"


def test_get_serial_device_not_found(mock_subprocess: MagicMock):
    mock_subprocess.return_value = b"Asdf, CircuitPython CDC control@sda1"
    result = get_serial_device()

    assert result == ""
