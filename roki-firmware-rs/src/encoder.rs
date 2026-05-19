/// Rotary encoder task using the nRF QDEC peripheral.

use embassy_nrf::gpio::AnyPin;
use embassy_nrf::peripherals::QDEC;
use embassy_nrf::qdec::{self, Qdec, SamplePeriod};
use embassy_sync::blocking_mutex::raw::ThreadModeRawMutex;
use embassy_sync::channel::Sender;

use crate::keymap::EncoderEvent;
use crate::logging::debug;

#[embassy_executor::task]
pub async fn encoder_task(
    qdec_peripheral: QDEC,
    pin_a: AnyPin,
    pin_b: AnyPin,
    tx: Sender<'static, ThreadModeRawMutex, EncoderEvent, 4>,
) {
    let config = qdec::Config::default()
        .sample_period(SamplePeriod::_2048US)
        .led_preuse(false);

    let mut qdec = Qdec::new(qdec_peripheral, pin_a, pin_b, None, config);
    let mut last_pos: i32 = 0;

    debug!("Encoder task started");

    loop {
        let report = qdec.read().await;
        if let Some(pos) = report.acc() {
            let diff = pos - last_pos;
            last_pos = pos;

            if diff > 0 {
                let _ = tx.send(EncoderEvent { delta: diff as i8 }).await;
            } else if diff < 0 {
                let _ = tx.send(EncoderEvent { delta: diff as i8 }).await;
            }
        }
    }
}
