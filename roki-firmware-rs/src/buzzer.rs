use embassy_nrf::gpio::AnyPin;
use embassy_nrf::peripherals::PWM0;
use embassy_nrf::pwm::{Prescaler, SimplePwm};
use embassy_sync::blocking_mutex::raw::ThreadModeRawMutex;
use embassy_sync::channel::{Channel, Receiver};
use embassy_time::{Duration, Timer};

use crate::logging::info;

// ── Note frequencies (Hz) ────────────────────────────────────────────────

pub fn note_frequency(note: &str) -> Option<u32> {
    match note {
        "C1" => Some(33),  "D1" => Some(37),  "E1" => Some(41),
        "F1" => Some(44),  "G1" => Some(49),  "A1" => Some(55),
        "B1" => Some(62),  "C2" => Some(65),  "D2" => Some(73),
        "E2" => Some(82),  "F2" => Some(87),  "G2" => Some(98),
        "A2" => Some(110), "B2" => Some(123), "C3" => Some(131),
        "D3" => Some(147), "E3" => Some(165), "F3" => Some(175),
        "G3" => Some(196), "A3" => Some(220), "B3" => Some(246),
        "C4" => Some(262), "D4" => Some(294), "E4" => Some(330),
        "F4" => Some(349), "G4" => Some(392), "A4" => Some(440),
        "B4" => Some(494),
        _ => None,
    }
}

// ── Buzzer struct ────────────────────────────────────────────────────────

pub struct Buzzer {
    pwm: SimplePwm<'static, PWM0>,
}

impl Buzzer {
    pub fn new(pwm: PWM0, pin: AnyPin) -> Self {
        let mut pwm = SimplePwm::new_1ch(pwm, pin);
        pwm.set_prescaler(Prescaler::Div128);
        pwm.set_duty(0, 0);
        Self { pwm }
    }

    pub fn tone(&mut self, freq: u32, _duration_ms: u16) {
        self.pwm.set_period(freq);
        // 50% duty cycle ≈ max volume without distortion on a piezo
        self.pwm.set_duty(0, (self.pwm.max_duty() + 1) / 2);
        // The caller must sleep for `duration_ms` before stopping.
        // Non-blocking: actual timing is handled in the task.
    }

    pub fn silence(&mut self) {
        self.pwm.set_duty(0, 0);
    }

    /// Queue a startup tone sequence into the channel.
    pub async fn queue_startup_tone() {
        // C3, D3, E3 ascending
        let _ = COMMAND_CHANNEL.send(BuzzerCommand::Sequence(&[
            ("C3", 150), ("D3", 150), ("E3", 300),
        ])).await;
    }

    /// Queue an error tone.
    pub async fn queue_error_tone() {
        let _ = COMMAND_CHANNEL.send(BuzzerCommand::Sequence(&[
            ("C1", 100), ("", 50), ("C1", 200),
        ])).await;
    }

    /// Queue a peripheral-connected tone.
    pub async fn queue_peripheral_connected_tone() {
        let _ = COMMAND_CHANNEL.send(BuzzerCommand::Sequence(&[
            ("C3", 100), ("", 50), ("D3", 200),
        ])).await;
    }
}

// ── Task-level command channel ───────────────────────────────────────────

pub static COMMAND_CHANNEL: Channel<ThreadModeRawMutex, BuzzerCommand, 4> = Channel::new();

pub enum BuzzerCommand {
    /// Play a sequence of (note, duration_ms) tuples.
    /// An empty note string `""` is a rest.
    Sequence(&'static [(&'static str, u16)]),
    /// Stop immediately and clear.
    Stop,
}

#[embassy_executor::task]
pub async fn buzzer_task(mut buzzer: Buzzer) {
    let rx: Receiver<'static, ThreadModeRawMutex, BuzzerCommand, 4> = COMMAND_CHANNEL.receiver();

    loop {
        match rx.receive().await {
            BuzzerCommand::Sequence(seq) => {
                info!("Playing tone sequence");
                for (note, ms) in seq {
                    if let Some(freq) = note_frequency(note) {
                        buzzer.tone(freq, *ms);
                    } else {
                        buzzer.silence();
                    }
                    Timer::after(Duration::from_millis(*ms as u64)).await;
                    buzzer.silence();
                }
            }
            BuzzerCommand::Stop => {
                buzzer.silence();
            }
        }
    }
}
