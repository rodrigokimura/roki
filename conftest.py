import sys
from unittest.mock import MagicMock

MOCK_MODULES = [
    "board",
    "rotaryio",
    "keypad",
    "digitalio",
    "usb_hid",
    "adafruit_ble.characteristics.Characteristic",
    "adafruit_ble.characteristics.ComplexCharacteristic",
    "adafruit_ble.services.standard.hid.HIDService",
    "adafruit_ble.attributes.Attribute",
    "adafruit_ble.uuid.VendorUUID",
    "adafruit_ble.advertising.standard.ProvideServicesAdvertisement",
    "adafruit_ble.services.standard.device_info.DeviceInfoService",
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
    mock_imported_modules()


mock_imported_modules()
