import sys
from unittest.mock import MagicMock

MOCK_MODULES = [
    "board",
    "rotaryio",
    "keypad",
    "digitalio",
    "analogio",
    "usb_hid",
    "adafruit_hid",
    "adafruit_hid.consumer_control",
    "adafruit_hid.consumer_control_code",
    "adafruit_hid.keyboard",
    "adafruit_hid.keycode",
    "adafruit_hid.mouse",
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
