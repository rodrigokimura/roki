import board

from roki.firmware import logging
from roki.firmware.params import Params


Params.from_env()

logger = logging.getLogger(__name__)


def main():
    from roki.firmware.kb import Roki

    # pin mapping for the nice!nano
    roki = Roki.build(
        row_pins=("P0_24", "P1_00", "P0_11", "P1_04", "P1_06"),
        column_pins=("P0_09", "P0_10", "P1_11", "P1_13", "P1_15", "P0_02"),
        buzzer_pin="P0_06",
        thumb_stick_pins=("P0_22", "AIN7", "AIN5"),
        encoder_pins=("P0_17", "P0_20"),
    )
    roki.run()


if __name__ == "__main__":
    logger.debug("Available attrs for board: ")
    logger.debug(str(dir(board)))

    logger.info("Board ID: " + board.board_id)

    main()
