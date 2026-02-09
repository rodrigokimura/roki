import runpy
from unittest.mock import MagicMock, patch

import pytest

from roki.firmware.params import Params


@pytest.fixture
def mock_params_from_env():
    with patch.object(Params, "from_env") as m:
        yield m


@pytest.fixture
def mock_primary_init():
    from roki.firmware.kb import Primary

    with patch.object(Primary, "__init__") as m:
        m.return_value = None
        yield m


@pytest.fixture
def mock_secondary_init():
    from roki.firmware.kb import Secondary

    with patch.object(Secondary, "__init__") as m:
        m.return_value = None
        yield m


@pytest.fixture
def mock_roki_run():
    from roki.firmware.kb import Roki

    with patch.object(Roki, "run") as m:
        m.return_value = None
        yield m


def test_main_block(
    mock_primary_init: MagicMock,
    mock_roki_run: MagicMock,
    mock_hid_service: MagicMock,
):
    runpy.run_module("roki.firmware.code", run_name="__main__")
    mock_primary_init.assert_called_once()
    mock_roki_run.assert_called_once()
