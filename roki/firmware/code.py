import asyncio

import board

from roki.firmware.calibration import Calibration
from roki.firmware.kb import Roki
from roki.firmware.utils import blink_led


async def main():
    # pin mapping for the nice!nano
    rows = ("P0_24", "P1_00", "P0_11", "P1_04", "P1_06")
    cols = ("P0_09", "P0_10", "P1_11", "P1_13", "P1_15", "P0_02")
    encoder_pins = ("P0_17", "P0_20")
    # thumb_stick_pins = ("P0_31", "P0_29")
    thumb_stick_pins = ("AIN7", "AIN5")
    thumb_stick_button = "P0_22"

    roki = Roki.build(rows, cols, thumb_stick_pins, encoder_pins)
    await roki.run()


if __name__ == "__main__":
    print(dir(board))
    with Calibration():
        pass

    blink_led()
    asyncio.run(main())
