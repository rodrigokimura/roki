from unittest.mock import MagicMock, patch
import typer
from typer.testing import CliRunner


import pytest


@pytest.fixture
def app():
    from roki.cli.app import app

    return app


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_get_devices():
    with patch("roki.cli.app.get_devices") as m:
        m.return_value = ["sda1"]
        yield m


@pytest.fixture
def mock_copy_tree():
    with patch("roki.cli.app.copy_tree") as m:
        m.return_value = None
        yield m


@pytest.fixture
def mock_create_tree():
    with patch("roki.cli.app.create_tree") as m:
        m.return_value = None
        yield m


@pytest.fixture
def mock_create_empty_file():
    with patch("roki.cli.app.create_empty_file") as m:
        m.return_value = None
        yield m


@pytest.fixture
def mock_delete_file():
    with patch("roki.cli.app.delete_file") as m:
        m.return_value = None
        yield m


@pytest.fixture
def mock_delete_files_by_extension():
    with patch("roki.cli.app.delete_files_by_extension") as m:
        m.return_value = None
        yield m


@pytest.fixture
def mock_create_mount_point():
    with patch("roki.cli.app.create_mount_point") as m:
        m.return_value = None
        yield m


@pytest.fixture
def mock_unmount():
    with patch("roki.cli.app.unmount") as m:
        m.return_value = None
        yield m


@pytest.fixture
def mock_install_circuitpython_libs():
    with patch("roki.cli.app.install_circuitpython_libs") as m:
        m.return_value = None
        yield m


def test_app(
    runner: CliRunner,
    app: typer.Typer,
):
    result = runner.invoke(app, ["--help"])
    result.exit_code = 0

    assert "roki" in result.stdout


def test_app_upload(
    runner: CliRunner,
    app: typer.Typer,
    mock_get_devices: MagicMock,
    mock_copy_tree: MagicMock,
    mock_create_tree: MagicMock,
    mock_create_empty_file: MagicMock,
    mock_delete_file: MagicMock,
    mock_delete_files_by_extension: MagicMock,
    mock_create_mount_point: MagicMock,
    mock_install_circuitpython_libs: MagicMock,
    mock_unmount: MagicMock,
):
    side = "right"
    result = runner.invoke(app, ["upload", "--side", side])

    assert result.exit_code == 0

    mock_copy_tree.assert_called()
    mock_create_tree.assert_called()
    mock_create_empty_file.assert_called()
    mock_delete_file.assert_called()
    mock_delete_files_by_extension.assert_called()
    mock_install_circuitpython_libs.assert_called()
    mock_unmount.assert_called()
    mock_create_mount_point.assert_called()
    mock_get_devices.assert_called()
