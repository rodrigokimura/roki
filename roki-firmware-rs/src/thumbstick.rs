use embassy_nrf::gpio::{Input, Pull};
use embassy_nrf::peripherals::SAADC;
use embassy_nrf::saadc::{self, Saadc};
use embassy_sync::blocking_mutex::raw::ThreadModeRawMutex;
use embassy_sync::channel::Sender;
use embassy_time::{Duration, Instant, Timer};

use crate::buzzer::Buzzer;
use crate::calibration::{CalibrationData, NormalizedCalibration};
use crate::keymap::ThumbstickEvent;
use crate::logging::{debug, info, trace};

// Bind SAADC interrupt.
embassy_nrf::bind_interrupts!(struct Irqs {
    SAADC => saadc::InterruptHandler;
});

#[embassy_executor::task]
pub async fn thumbstick_task(
    saadc_peripheral: SAADC,
    pin_x: embassy_nrf::peripherals::P0_31,
    pin_y: embassy_nrf::peripherals::P0_29,
    pin_switch: embassy_nrf::peripherals::P0_22,
    calibration: NormalizedCalibration,
    tx: Sender<'static, ThreadModeRawMutex, ThumbstickEvent, 4>,
) {
    // Two single-ended channels
    let mut channel_cfg_x = saadc::ChannelConfig::single_ended(pin_x);
    channel_cfg_x.gain = saadc::Gain::GAIN1_6;
    channel_cfg_x.reference = saadc::Reference::INTERNAL;
    channel_cfg_x.time = saadc::Time::_10US;

    let mut channel_cfg_y = saadc::ChannelConfig::single_ended(pin_y);
    channel_cfg_y.gain = saadc::Gain::GAIN1_6;
    channel_cfg_y.reference = saadc::Reference::INTERNAL;
    channel_cfg_y.time = saadc::Time::_10US;

    let config = saadc::Config::default();

    let mut saadc = Saadc::new(
        saadc_peripheral,
        Irqs,
        config,
        [channel_cfg_x, channel_cfg_y],
    );

    let switch = Input::new(pin_switch, Pull::Up);

    // ── Boot-time calibration ─────────────────────────────────────────
    let calibration = if !switch.is_high() {
        info!("Thumbstick switch held at boot — entering calibration mode");
        let new_cal = run_boot_calibration(&mut saadc, &switch).await;
        new_cal.save_to_flash();
        NormalizedCalibration::from_data(&new_cal)
    } else {
        calibration
    };

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

/// Run the boot-time calibration procedure using an already-initialized SAADC.
///
/// Flow:
/// 1. Play start tone, wait for user to release switch.
/// 2. Sample neutral (center) position for 5 s.
/// 3. Play rotation tone; user rotates stick to all edges.
/// 4. Stop when switch is pressed again; save min/max + mid values.
async fn run_boot_calibration(saadc: &mut Saadc<'_, 2>, switch: &Input<'_>) -> CalibrationData {
    let mut buf = [0i16; 2];

    // 1. Start tone + wait for release
    Buzzer::queue_startup_tone().await;
    info!("Release thumbstick switch to begin center sampling...");
    while !switch.is_high() {
        Timer::after(Duration::from_millis(10)).await;
    }
    Timer::after(Duration::from_millis(500)).await; // debounce

    // 2. Sample center (mid) for 5 s
    info!("Sampling center — hold thumbstick neutral for 5 s...");
    let mut sum_x: i32 = 0;
    let mut sum_y: i32 = 0;
    let mut samples: u32 = 0;
    let start = Instant::now();
    while start.elapsed() < Duration::from_secs(5) {
        saadc.sample(&mut buf).await;
        sum_x += buf[0] as i32;
        sum_y += buf[1] as i32;
        samples += 1;
        Timer::after(Duration::from_millis(50)).await;
    }
    let mid_x = (sum_x / samples as i32) as i16;
    let mid_y = (sum_y / samples as i32) as i16;
    info!("Center sampled: x={} y={}", mid_x, mid_y);

    // 3. Rotation tone + sample min/max
    Buzzer::queue_peripheral_connected_tone().await;
    info!("Rotate thumbstick to all edges, then press switch to finish...");
    let mut min_x = mid_x;
    let mut max_x = mid_x;
    let mut min_y = mid_y;
    let mut max_y = mid_y;
    loop {
        saadc.sample(&mut buf).await;
        let x = buf[0];
        let y = buf[1];
        if x < min_x { min_x = x; }
        if x > max_x { max_x = x; }
        if y < min_y { min_y = y; }
        if y > max_y { max_y = y; }
        if !switch.is_high() {
            break;
        }
        Timer::after(Duration::from_millis(10)).await;
    }
    info!(
        "Extents sampled: x=[{}, {}] y=[{}, {}]",
        min_x, max_x, min_y, max_y
    );

    CalibrationData {
        min_x,
        mid_x,
        max_x,
        min_y,
        mid_y,
        max_y,
    }
}
