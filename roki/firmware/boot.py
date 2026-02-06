import board
import digitalio
import storage

from roki.firmware import logging
from roki.firmware.params import Params

Params.from_env()

logger = logging.getLogger(__name__)

pin = "P0_22"
switch = digitalio.DigitalInOut(getattr(board, pin))
switch.direction = digitalio.Direction.INPUT
switch.pull = digitalio.Pull.UP

logger.debug(f"Switch state ({pin}): {switch.value}")

try:
    storage.remount("/", readonly=switch.value)
except RuntimeError as e:
    logger.error(str(e))

switch.deinit()
