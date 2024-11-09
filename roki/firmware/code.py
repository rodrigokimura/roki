from roki.firmware.kb import Roki


def main():
    # pin mapping for the nice!nano
    rows = ("P0_24", "P1_00", "P0_11", "P1_04", "P1_06")
    cols = ("P0_09", "P0_10", "P1_11", "P1_13", "P1_15", "P0_02")
    encoder_pins = ("P0_17", "P0_20")

    roki = Roki.build(rows, cols, encoder_pins)
    roki.run()


if __name__ == "__main__":
    main()
