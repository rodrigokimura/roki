import board
import digitalio
import storage

switch = digitalio.DigitalInOut(getattr(board, "P0_22"))
switch.direction = digitalio.Direction.INPUT
switch.pull = digitalio.Pull.UP

print(switch.value)
storage.remount("/", readonly=switch.value)
switch.deinit()
