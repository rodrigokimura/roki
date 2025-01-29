from unittest.mock import MagicMock, patch

import pytest

from roki.cli.file_management import (
    copy_file,
    copy_tree,
    create_empty_file,
    create_tree,
    delete_file,
    delete_files_by_extension,
)


@pytest.fixture
def mock_run_command():
    with patch("roki.cli.file_management.run_command") as m:
        yield m


def test_delete_files_by_extension(mock_run_command: MagicMock):
    delete_files_by_extension(["xxx"], ".")
    mock_run_command.assert_called_once_with("sudo rm ./*.xxx -vf", shell=True)


def test_create_tree(mock_run_command: MagicMock):
    create_tree("abc/def")
    mock_run_command.assert_called_once_with("sudo mkdir abc/def -p", shell=True)


def test_copy_tree(mock_run_command: MagicMock):
    copy_tree("abc/def", ".")
    mock_run_command.assert_called_once_with("sudo cp abc/def/* . -rpvf", shell=True)


def test_copy_tree_with_extensions(mock_run_command: MagicMock):
    copy_tree("abc/def", ".", ["txt", "py"])
    calls = mock_run_command.call_args_list
    assert len(calls) == 2
    call1, call2 = calls
    assert call1.args == ("sudo cp abc/def/*.txt . -rpvf",)
    assert call2.args == ("sudo cp abc/def/*.py . -rpvf",)


def test_copy_file(mock_run_command: MagicMock):
    copy_file("abc/def.txt", "xyz")
    mock_run_command.assert_called_once_with("sudo cp abc/def.txt xyz/ -vf", shell=True)


def test_create_empty_file(mock_run_command: MagicMock):
    create_empty_file("abc/def.txt")
    mock_run_command.assert_called_once_with("sudo touch abc/def.txt", shell=True)


def test_delete_file(mock_run_command: MagicMock):
    delete_file("abc/def.txt")
    mock_run_command.assert_called_once_with("sudo rm abc/def.txt -vf", shell=True)
