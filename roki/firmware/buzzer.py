import time

import pwmio


class Buzzer:
    def __init__(self, pwm_pin: pwmio.PWMOut):
        self.pwm_pin = pwm_pin

    def play_by_frequency(self, frequency: int, duration: float):
        OFF = 0
        ON = 2**15
        self.pwm_pin.duty_cycle = ON
        self.pwm_pin.frequency = frequency
        time.sleep(duration)
        self.pwm_pin.duty_cycle = OFF

    def pause(self, duration: float):
        time.sleep(duration)

    def play_by_note(self, note: str, duration: float):
        notes = {
            "C1": 33,
            "D1": 37,
            "E1": 41,
            "F1": 44,
            "G1": 49,
            "A1": 55,
            "B1": 62,
            "C2": 65,
            "D2": 73,
            "E2": 82,
            "F2": 87,
            "G2": 98,
            "A2": 110,
            "B2": 123,
            "C3": 131,
            "D3": 147,
            "E3": 165,
            "F3": 175,
            "G3": 196,
            "A3": 220,
            "B3": 246,
            "C4": 262,
            "D4": 294,
            "E4": 330,
            "F4": 349,
            "G4": 392,
            "A4": 440,
            "B4": 494,
        }
        if note in notes:
            self.play_by_frequency(notes[note], duration)
        else:
            self.pause(duration)

    def play_notes(self, notes: tuple[tuple[str, int], ...], duration: float):
        for note, multiple in notes:
            self.play_by_note(note, multiple * duration)
