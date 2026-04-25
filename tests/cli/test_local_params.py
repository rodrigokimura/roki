from importlib import import_module
from unittest.mock import patch


def test_local_params():
    from roki.firmware.params import Params

    with patch.object(Params, "__init__") as m:
        m.return_value = None

        import_module("roki.cli.local_params")

        m.assert_called()
