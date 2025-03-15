import sys
from unittest.mock import MagicMock

MOCK_MODULES = [
    "board",
    "rotaryio",
    "digitalio",
    "pwmio",
    "analogio",
    "usb_hid",
    "_bleio",
]


def mock_imported_modules():
    module_paths = set()
    for m in MOCK_MODULES:
        namespaces = m.split(".")
        ns = []
        for n in namespaces:
            ns.append(n)
            module_paths.add(".".join(ns))
    for m_path in module_paths:
        sys.modules[m_path] = MagicMock()


def pytest_runtest_setup(item):
    lambda: item  # HACK: avoid LSP flagging as non-used name
    mock_imported_modules()
