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


@pytest.fixture(autouse=True)
def mock_get_devices():
    with patch("roki.cli.app.get_devices") as m:
        m.return_value = ["sda1"]
        yield m


@pytest.fixture(autouse=True)
def mock_copy_tree():
    with patch("roki.cli.app.copy_tree") as m:
        m.return_value = None
        yield m


@pytest.fixture(autouse=True)
def mock_create_tree():
    with patch("roki.cli.app.create_tree") as m:
        m.return_value = None
        yield m


@pytest.fixture(autouse=True)
def mock_create_empty_file():
    with patch("roki.cli.app.create_empty_file") as m:
        m.return_value = None
        yield m


@pytest.fixture(autouse=True)
def mock_delete_file():
    with patch("roki.cli.app.delete_file") as m:
        m.return_value = None
        yield m


@pytest.fixture(autouse=True)
def mock_delete_files_by_extension():
    with patch("roki.cli.app.delete_files_by_extension") as m:
        m.return_value = None
        yield m


@pytest.fixture(autouse=True)
def mock_create_mount_point():
    with patch("roki.cli.app.create_mount_point") as m:
        m.return_value = None
        yield m


@pytest.fixture(autouse=True)
def mock_unmount():
    with patch("roki.cli.app.unmount") as m:
        m.return_value = None
        yield m


@pytest.fixture(autouse=True)
def mock_install_circuitpython_libs():
    with patch("roki.cli.app.install_circuitpython_libs") as m:
        m.return_value = None
        yield m


@pytest.fixture(autouse=True)
def mock_debug_codes():
    with patch("roki.cli.app.debug_codes") as m:
        m.return_value = None
        yield m


@pytest.fixture(autouse=True)
def mock_generate():
    from roki.cli.html_generator import Generator

    with patch.object(Generator, "generate_html") as m:
        m.return_value = None
        yield m


@pytest.fixture(autouse=True)
def mock_uvicorn():
    with patch("roki.cli.app.uvicorn") as m:
        yield m


@pytest.fixture(autouse=True)
def mock_config_run():
    from roki.tui.app import Configurator

    with patch.object(Configurator, "run") as m:
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


def test_app_upload_no_devices(
    runner: CliRunner,
    app: typer.Typer,
    mock_get_devices: MagicMock,
):
    mock_get_devices.return_value = []
    side = "right"
    result = runner.invoke(app, ["upload", "--side", side])

    assert result.exit_code == 1

    mock_get_devices.assert_called()


def test_app_upload_invalid_side(
    runner: CliRunner,
    app: typer.Typer,
):
    side = "invalid-value"
    result = runner.invoke(app, ["upload", "--side", side])

    assert result.exit_code == 1


def test_app_upload_multiple_devices_invalid_value(
    runner: CliRunner,
    app: typer.Typer,
    mock_get_devices: MagicMock,
):
    mock_get_devices.return_value = ["sda1", "sda2"]
    side = "right"
    result = runner.invoke(app, ["upload", "--side", side], input="not-a-number")

    assert result.exit_code == 1
    assert "not a number" in result.stdout.lower()


def test_app_upload_multiple_devices_invalid_option(
    runner: CliRunner,
    app: typer.Typer,
    mock_get_devices: MagicMock,
):
    mock_get_devices.return_value = ["sda1", "sda2"]
    side = "right"
    result = runner.invoke(app, ["upload", "--side", side], input="99")

    assert result.exit_code == 1
    assert "not an option" in result.stdout.lower()


def test_app_upload_multiple_devices(
    runner: CliRunner,
    app: typer.Typer,
    mock_get_devices: MagicMock,
):
    mock_get_devices.return_value = ["sda1", "sda2"]
    side = "right"
    result = runner.invoke(app, ["upload", "--side", side], input="1")

    assert result.exit_code == 0


def test_app_run(
    runner: CliRunner,
    app: typer.Typer,
    mock_debug_codes: MagicMock,
):
    result = runner.invoke(app, ["run"])

    assert result.exit_code == 0
    mock_debug_codes.assert_called()


def test_app_serve(
    runner: CliRunner,
    app: typer.Typer,
    mock_generate: MagicMock,
    mock_uvicorn: MagicMock,
):
    result = runner.invoke(app, ["serve"], input="...")

    assert result.exit_code == 0
    mock_generate.assert_called()
    mock_uvicorn.run.assert_called()


def test_app_generate(
    runner: CliRunner,
    app: typer.Typer,
    mock_generate: MagicMock,
):
    result = runner.invoke(app, ["generate"])

    assert result.exit_code == 0
    mock_generate.assert_called()


def test_app_config(
    runner: CliRunner,
    app: typer.Typer,
    mock_config_run: MagicMock,
):
    result = runner.invoke(app, ["config"])

    assert result.exit_code == 0
    mock_config_run.assert_called()
