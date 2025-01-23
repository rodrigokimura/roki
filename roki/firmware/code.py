import asyncio

import board

from roki.firmware.kb import Roki


async def main():
    # pin mapping for the nice!nano
    rows = ("P0_24", "P1_00", "P0_11", "P1_04", "P1_06")
    cols = ("P0_09", "P0_10", "P1_11", "P1_13", "P1_15", "P0_02")
    encoder_pins = ("P0_17", "P0_20")
    thumb_stick_pins = ("P0_22", "AIN7", "AIN5")

    roki = Roki.build(rows, cols, thumb_stick_pins, encoder_pins)
    await roki.run()


if __name__ == "__main__":
    print(dir(board))

    asyncio.run(main())
