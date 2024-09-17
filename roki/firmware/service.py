from adafruit_ble.characteristics.int import IntCharacteristic
from adafruit_ble.services import Service
from adafruit_ble.uuid import VendorUUID


class RowCharacteristic(IntCharacteristic):
    def __init__(self, *, min_value: int = 0, max_value: int = 4, **kwargs) -> None:
        super().__init__("<i", min_value, max_value, **kwargs)


class ColumnCharacteristic(IntCharacteristic):
    def __init__(self, *, min_value: int = 0, max_value: int = 5, **kwargs) -> None:
        super().__init__("<i", min_value, max_value, **kwargs)


class StateCharacteristic(IntCharacteristic):
    def __init__(self, *, min_value: int = 0, max_value: int = 1, **kwargs) -> None:
        super().__init__("<i", min_value, max_value, **kwargs)


class RokiService(Service):
    uuid = VendorUUID("d0a37544-a8d9-462c-950a-43f103748eb4")
    row = RowCharacteristic(
        uuid=VendorUUID("2c305b04-3ef7-4771-aa1a-3130d352f895"),
    )
    column = ColumnCharacteristic(
        uuid=VendorUUID("0a13e4a8-d291-4edf-8ac8-ea72a1395443")
    )
    state = StateCharacteristic(uuid=VendorUUID("00596aeb-e3c5-4e50-9d60-634888ea1d77"))

    def __init__(self, service=None) -> None:
        super().__init__(service=service)
        self.connectable = True
