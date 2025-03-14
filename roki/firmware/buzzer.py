import time

import pwmio


def play(buzzer: pwmio.PWMOut):

    OFF = 0
    ON = 2**15
    buzzer.duty_cycle = ON
    buzzer.frequency = 262  # C4
    time.sleep(0.5)
    # buzzer.frequency = 294  # D4
    # buzzer.frequency = 330  # E4
    buzzer.duty_cycle = OFF
