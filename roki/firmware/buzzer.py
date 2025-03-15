import time

import pwmio


class Buzzer:
    def __init__(self, pwm_pin: pwmio.PWMOut):
        self.pwm_pin = pwm_pin

    def play(self, frequency: int, duration: float):
        self.pwm_pin.duty_cycle = 0
        self.pwm_pin.frequency = frequency
        time.sleep(duration)
        self.pwm_pin.duty_cycle = 2**15


def play(buzzer: pwmio.PWMOut):
    buzzer.duty_cycle = ON
    buzzer.frequency = 262  # C4
    time.sleep(0.5)
    # buzzer.frequency = 294  # D4
    # buzzer.frequency = 330  # E4
    buzzer.duty_cycle = OFF
