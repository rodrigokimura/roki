from roki.cli.html_generator import Generator

import pytest


@pytest.fixture
def generator():
    return Generator()


def test_generate_keys(generator: Generator):
    result = generator.get_html()
    print(result)
