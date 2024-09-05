import adafruit_ble
import time
import board
from adafruit_ble.advertising import Advertisement
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.standard.device_info import DeviceInfoService

from keypad import KeyMatrix

from roki.firmware.config import Config
from roki.firmware.keys import HID

ROWS = ["P0_24", "P1_00", "P0_11", "P1_04", "P1_06"]
COLS = ["P0_09", "P0_10", "P1_11", "P1_13", "P1_15", "P0_02"]
COLUMNS_TO_ANODES = False
INTERVAL = 0.01
MAX_EVENTS = 30


def main():
    hid = HID
    key_matrix = KeyMatrix(
        row_pins=tuple(getattr(board, pin) for pin in ROWS),
        column_pins=tuple(getattr(board, pin) for pin in COLS),
        columns_to_anodes=COLUMNS_TO_ANODES,
        interval=INTERVAL,
        max_events=MAX_EVENTS,
    )

    device_info = DeviceInfoService(
        software_revision=adafruit_ble.__version__,
        manufacturer="Adafruit Industries",
    )
    advertisement = ProvideServicesAdvertisement(hid)
    # Advertise as "Keyboard" (0x03C1) icon when pairing
    # https://www.bluetooth.com/specifications/assigned-numbers/
    advertisement.appearance = 961
    scan_response = Advertisement()
    scan_response.complete_name = "Roki"

    ble = adafruit_ble.BLERadio()
    ble.name = "Roki"
    if ble.connected:
        print("already connected")
        for c in ble.connections:
            if c:
                c.disconnect()

    print("advertising")
    ble.start_advertising(
        advertisement,
        scan_response,
        # interval=0.5,
        # timeout=60,
    )

    print("config created")
    config = Config.read()
    while True:
        while not ble.connected:
            pass
            # print("skipping...")
            # time.sleep(0.1)

        # print("Start typing:")
        # print(".", end="")

        while ble.connected:
            event = key_matrix.events.get()
            if event:
                row, col = get_coords(event.key_number, len(COLS))

                key = config.layer.primary_keys[row][col]
                print(key.key_names)

                if event.pressed:
                    key.press()
                else:
                    key.release()

        ble.start_advertising(
            advertisement,
            # scan_response,
        )


def get_coords(i: int, col_count: int = 6):
    c = i % col_count
    r = i // col_count
    return r, c


if __name__ == "__main__":
    main()
    # print(dir(board))
