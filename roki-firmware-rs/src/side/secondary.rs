use core::sync::atomic::{AtomicBool, Ordering};
use embassy_sync::blocking_mutex::raw::ThreadModeRawMutex;
use embassy_sync::channel::Receiver;
use embassy_time::{Duration, Timer};
use nrf_softdevice::ble::advertisement_builder::{AdvertisementBuilder, Flag, ServiceList};
use nrf_softdevice::ble::peripheral::{advertise_connectable, ConnectableAdvertisement, Config as AdvConfig};

use crate::ble::roki_service::{RokiServer, ROKI_UUID_128};
use crate::buzzer::Buzzer;
use crate::config::Config;
use crate::keymap::{EncoderEvent, KeyAction, KeyEvent, ThumbstickEvent};
use crate::layers::{LayerCommand, LayerHandler};
use crate::logging::{info, trace};
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

    // ── Enable SoftDevice and register RokiService ───────────────────────
    let sd = crate::ble::init_softdevice();
    let server = match RokiServer::register(sd) {
        Ok(s) => s,
        Err(e) => {
            info!("Failed to register RokiService: {}", defmt::Debug2Format(&e));
            return;
        }
    };

    // Build advertisement data with our 128-bit service UUID
    let adv_data = AdvertisementBuilder::<31>::new()
        .flags(&[Flag::GeneralDiscovery, Flag::LE_Only])
        .services_128(ServiceList::Complete, &[ROKI_UUID_128])
        .short_name("Roki")
        .build();
    let scan_resp = &[];

    info!("Advertising RokiService...");
    let conn = match advertise_connectable(
        sd,
        ConnectableAdvertisement::ScannableUndirected {
            adv_data: adv_data.as_ref(),
            scan_data: scan_resp,
        },
        &AdvConfig::default(),
    )
    .await
    {
        Ok(c) => {
            info!("Primary connected: {:x}", c.peer_address().bytes());
            Buzzer::queue_peripheral_connected_tone().await;
            c
        }
        Err(e) => {
            info!("Advertising failed: {}", defmt::Debug2Format(&e));
            return;
        }
    };

    // ── Main loop: process inputs and notify ─────────────────────────────
    let mut counter = Cycle::new(0, 100);
    let layer = LayerHandler::<8>::new();
    let mut send_thumb = false;

    loop {
        if let Ok(event) = key_rx.try_receive() {
            counter.increment();
            let current_layer = config.layers.get(layer.current()).unwrap();
            let key = current_layer.secondary_keys[event.index as usize];

            if event.pressed {
                if let KeyAction::Layer(LayerCommand::ToggleExtras) = key {
                    let extras = EXTRAS.load(Ordering::Relaxed);
                    EXTRAS.store(!extras, Ordering::Relaxed);
                }
            }

            if !matches!(key, KeyAction::Layer(_)) {
                let packet = protocol::pack_packet(
                    counter.value(),
                    protocol::KEY,
                    (event.index, event.pressed as u8),
                );
                server.notify(&conn, &packet);
                trace!("TX KEY packet: {:?}", packet);
            }
        }

        if let Ok(event) = encoder_rx.try_receive() {
            if !EXTRAS.load(Ordering::Relaxed) {
                continue;
            }
            counter.increment();
            let packet = if event.delta > 0 {
                protocol::pack_packet(counter.value(), protocol::ENCODER, (event.delta as u8, 0))
            } else {
                protocol::pack_packet(counter.value(), protocol::ENCODER, (0, (-event.delta) as u8))
            };
            server.notify(&conn, &packet);
            trace!("TX ENCODER packet: {:?}", packet);
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
                server.notify(&conn, &packet);
                trace!("TX THUMB packet: {:?}", packet);
                send_thumb = true;
            } else if send_thumb {
                let packet = protocol::pack_packet(counter.value(), protocol::THUMB_STICK, (0, 0));
                server.notify(&conn, &packet);
                trace!("TX THUMB zero packet: {:?}", packet);
                send_thumb = false;
            }
        }

        Timer::after(Duration::from_micros(500)).await;
    }
}
