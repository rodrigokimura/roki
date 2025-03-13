import board

from roki.firmware.kb import Roki


def main():
    # pin mapping for the nice!nano
    Roki.build(
        row_pins=("P0_24", "P1_00", "P0_11", "P1_04", "P1_06"),
        column_pins=("P0_09", "P0_10", "P1_11", "P1_13", "P1_15", "P0_02"),
        thumb_stick_pins=("P0_22", "AIN7", "AIN5"),
        encoder_pins=("P0_17", "P0_20"),
    ).run()


if __name__ == "__main__":
    print(dir(board))
    # import microcontroller
    # import board
    #
    # for pin in dir(microcontroller.pin):
    #     if isinstance(getattr(microcontroller.pin, pin), microcontroller.Pin):
    #         print("".join(("microcontroller.pin.", pin, "\t")), end=" ")
    #         for alias in dir(board):
    #             if getattr(board, alias) is getattr(microcontroller.pin, pin):
    #                 print("".join(("", "board.", alias)), end=" ")
    #     print()

    main()
