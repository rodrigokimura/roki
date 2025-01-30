import pytest
from roki.cli.config.models import Key


@pytest.fixture
def key_a():
    return Key(name="A", value="A", description="``a`` and ``A``", icon="keyboard")


@pytest.fixture
def key_b():
    return Key(name="B", value="B", description="``b`` and ``B``", icon="keyboard")


def test_description(key_a: Key):
    assert key_a.description == "a and A"


def test_key_set(key_a: Key, key_b: Key):
    result = {key_a, key_b, key_a.model_copy()}
    assert len(result) == 2
