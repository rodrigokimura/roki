use core::sync::atomic::{AtomicBool, Ordering};
use embassy_sync::blocking_mutex::raw::ThreadModeRawMutex;
use embassy_sync::channel::Receiver;
use embassy_time::{Duration, Timer};

use crate::config::Config;
use crate::keymap::{EncoderEvent, KeyAction, KeyEvent, ThumbstickEvent};
use crate::layers::{LayerCommand, LayerHandler};
use crate::logging::info;
use crate::protocol;
use crate::utils::Cycle;

static EXTRAS: AtomicBool = AtomicBool::new(false);

#[embassy_executor::task]
pub async fn secondary_task(
    config: Config,
    key_rx: Receiver<'static, ThreadModeRawMutex, KeyEvent, 16>,
    encoder_rx: Receiver<'static, ThreadModeRawMutex, EncoderEvent, 4>,
    thumb_rx: Receiver<'static, ThreadModeRawMutex, ThumbstickEvent, 4>,
) {
    info!("Secondary (right) side starting");

    // TODO: Initialize SoftDevice peripheral mode
    // TODO: Create RokiService, start advertising

    let mut counter = Cycle::new(0, 100);
    let mut layer = LayerHandler::<8>::new();
    let mut send_thumb = false;

    loop {
        if let Ok(event) = key_rx.try_receive() {
            counter.increment();
            let current_layer = config.layers.get(layer.current()).unwrap();
            let key = current_layer.secondary_keys[event.index as usize];

            // Check for extras toggle
            if event.pressed {
                if let KeyAction::Layer(LayerCommand::ToggleExtras) = key {
                    let extras = EXTRAS.load(Ordering::Relaxed);
                    EXTRAS.store(!extras, Ordering::Relaxed);
                }
            }

            // Only send KEY message if it's not a layer command
            if !matches!(key, KeyAction::Layer(_)) {
                let packet = protocol::pack_packet(
                    counter.value(),
                    protocol::KEY,
                    (event.index, event.pressed as u8),
                );
                // TODO: send via RokiService.notify(conn, &packet)
                info!("TX KEY packet: {:?}", packet);
            }
        }

        if let Ok(event) = encoder_rx.try_receive() {
            if !EXTRAS.load(Ordering::Relaxed) {
                continue;
            }
            counter.increment();
            if event.delta > 0 {
                let packet = protocol::pack_packet(
                    counter.value(),
                    protocol::ENCODER,
                    (event.delta as u8, 0),
                );
                // TODO: notify
                info!("TX ENCODER CW packet: {:?}", packet);
            } else {
                let packet = protocol::pack_packet(
                    counter.value(),
                    protocol::ENCODER,
                    (0, (-event.delta) as u8),
                );
                // TODO: notify
                info!("TX ENCODER CCW packet: {:?}", packet);
            }
        }

        if let Ok(event) = thumb_rx.try_receive() {
            if !EXTRAS.load(Ordering::Relaxed) {
                continue;
            }
            counter.increment();
            if event.x != 0.0 || event.y != 0.0 {
                let packet = protocol::pack_packet(
                    counter.value(),
                    protocol::THUMB_STICK,
                    (protocol::encode_float(event.x), protocol::encode_float(event.y)),
                );
                // TODO: notify
                info!("TX THUMB packet: {:?}", packet);
                send_thumb = true;
            } else if send_thumb {
                let packet = protocol::pack_packet(
                    counter.value(),
                    protocol::THUMB_STICK,
                    (0, 0),
                );
                // TODO: notify
                info!("TX THUMB zero packet: {:?}", packet);
                send_thumb = false;
            }
        }

        Timer::after(Duration::from_micros(500)).await;
    }
}
