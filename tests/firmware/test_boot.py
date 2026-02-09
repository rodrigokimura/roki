from importlib import import_module
from unittest.mock import MagicMock, patch

import pytest

from roki.firmware.params import Params


@pytest.fixture
def mock_params_from_env():
    with patch.object(Params, "from_env") as m:
        yield m


def test_boot(mock_params_from_env: MagicMock):
    import_module("roki.firmware.boot")

    mock_params_from_env.assert_called_once()
