use embassy_nrf::gpio::{AnyPin, Input, Pull};
use embassy_nrf::peripherals::SAADC;
use embassy_nrf::saadc::{self, Saadc};
use embassy_sync::blocking_mutex::raw::ThreadModeRawMutex;
use embassy_sync::channel::Sender;
use embassy_time::{Duration, Timer};

use crate::calibration::NormalizedCalibration;
use crate::keymap::ThumbstickEvent;
use crate::logging::{debug, trace};

// Bind SAADC interrupt.
embassy_nrf::bind_interrupts!(struct Irqs {
    SAADC => saadc::InterruptHandler;
});

#[embassy_executor::task]
pub async fn thumbstick_task(
    saadc_peripheral: SAADC,
    pin_x: AnyPin,
    pin_y: AnyPin,
    pin_switch: AnyPin,
    calibration: NormalizedCalibration,
    tx: Sender<'static, ThreadModeRawMutex, ThumbstickEvent, 4>,
) {
    // Two single-ended channels
    let channel_cfg_x = saadc::ChannelConfig::single_ended(pin_x);
    let channel_cfg_y = saadc::ChannelConfig::single_ended(pin_y);

    let config = saadc::Config::default()
        .gain(saadc::Gain::GAIN1_6)
        .reference(saadc::Reference::INTERNAL)
        .resolution(saadc::Resolution::_12BIT);

    let mut saadc = Saadc::new(
        saadc_peripheral,
        Irqs,
        config,
        [channel_cfg_x, channel_cfg_y],
    );

    let switch = Input::new(pin_switch, Pull::Up);

    debug!("Thumbstick task started");

    let mut buf = [0i16; 2];

    loop {
        saadc.sample(&mut buf).await;
        let raw_x = buf[0];
        let raw_y = buf[1];

        let x = calibration.normalize_x(raw_x);
        let y = calibration.normalize_y(raw_y);
        let pressed = !switch.is_high(); // active low

        trace!("Thumbstick raw=({}, {}) norm=({:?}, {:?})", raw_x, raw_y, x, y);

        if x != 0.0 || y != 0.0 || pressed {
            let _ = tx.send(ThumbstickEvent { x, y, pressed }).await;
        }

        Timer::after(Duration::from_millis(10)).await;
    }
}
