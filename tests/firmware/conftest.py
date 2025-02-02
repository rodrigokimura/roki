import pytest
from unittest.mock import mock_open, patch


@pytest.fixture(autouse=True)
def mock_config_json():
    with open("roki/firmware/config.json") as f:
        config = f.read()
    with patch("builtins.open", mock_open(read_data=config)) as mock_file:
        yield mock_file
