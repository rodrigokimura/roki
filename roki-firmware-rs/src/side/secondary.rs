use embassy_sync::blocking_mutex::raw::ThreadModeRawMutex;
use embassy_sync::channel::Receiver;
use embassy_time::{Duration, Timer};

use crate::buzzer::Buzzer;
use crate::config::Config;
use crate::keymap::{EncoderEvent, KeyAction, KeyEvent, ThumbstickEvent};
use crate::layers::{LayerCommand, LayerHandler};
use crate::logging::{info, trace};
use crate::protocol;
use crate::utils::Cycle;

use core::sync::atomic::{AtomicBool, Ordering};

static EXTRAS: AtomicBool = AtomicBool::new(false);

#[embassy_executor::task]
pub async fn secondary_task(
    mut config: Config,
    mut key_rx: Receiver<'static, ThreadModeRawMutex, KeyEvent, 16>,
    mut encoder_rx: Receiver<'static, ThreadModeRawMutex, EncoderEvent, 4>,
    mut thumb_rx: Receiver<'static, ThreadModeRawMutex, ThumbstickEvent, 4>,
) {
    info!("Secondary (right) side starting");

    // TODO: Initialize SoftDevice peripheral mode
    // TODO: Create RokiService, start advertising

    let mut counter = Cycle::new(0, 100);
    let mut layer = LayerHandler::<8>::new();
    let mut send_thumb = false;

    loop {
        use embassy_futures::select::{select3, Either3};

        match select3(key_rx.receive(), encoder_rx.receive(), thumb_rx.receive()).await {
            Either3::First(event) => {
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
                    trace!("TX KEY packet: {:?}", packet);
                }
            }

            Either3::Second(event) => {
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
                    trace!("TX ENCODER CW packet: {:?}", packet);
                } else {
                    let packet = protocol::pack_packet(
                        counter.value(),
                        protocol::ENCODER,
                        (0, (-event.delta) as u8),
                    );
                    // TODO: notify
                    trace!("TX ENCODER CCW packet: {:?}", packet);
                }
            }

            Either3::Third(event) => {
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
                    trace!("TX THUMB packet: {:?}", packet);
                    send_thumb = true;
                } else if send_thumb {
                    let packet = protocol::pack_packet(
                        counter.value(),
                        protocol::THUMB_STICK,
                        (0, 0),
                    );
                    // TODO: notify
                    trace!("TX THUMB zero packet: {:?}", packet);
                    send_thumb = false;
                }
            }
        }
    }
}
