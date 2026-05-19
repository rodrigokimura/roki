use core::cell::RefCell;
use core::sync::atomic::{AtomicBool, Ordering};
use embassy_sync::blocking_mutex::raw::ThreadModeRawMutex;
use embassy_sync::blocking_mutex::Mutex;
use embassy_sync::channel::Receiver;
use embassy_time::{Duration, Timer};
use nrf_softdevice::ble::advertisement_builder::{AdvertisementBuilder, Flag, ServiceList};
use nrf_softdevice::ble::peripheral::{advertise_connectable, ConnectableAdvertisement, Config as AdvConfig};

use crate::ble::roki_service::{RokiServer, ROKI_UUID_128};
use crate::buzzer::Buzzer;
use crate::config::Config;
use crate::keymap::{EncoderEvent, KeyAction, KeyEvent, ThumbstickEvent};
use crate::layers::{LayerCommand, LayerHandler};
use crate::logging::{info, trace, warn};
use crate::protocol;
use crate::utils::Cycle;

// ── Cross-task shared connection to primary ─────────────────────────────
static PRIMARY_CONN: Mutex<ThreadModeRawMutex, RefCell<Option<nrf_softdevice::ble::Connection>>> =
    Mutex::new(RefCell::new(None));

static EXTRAS: AtomicBool = AtomicBool::new(false);

#[embassy_executor::task]
pub async fn secondary_task(
    config: Config,
    key_rx: Receiver<'static, ThreadModeRawMutex, KeyEvent, 16>,
    encoder_rx: Receiver<'static, ThreadModeRawMutex, EncoderEvent, 4>,
    thumb_rx: Receiver<'static, ThreadModeRawMutex, ThumbstickEvent, 4>,
) {
    info!("Secondary (right) side starting");

    let sd = crate::ble::init_softdevice();

    // Register RokiService once and keep it forever
    let server = match RokiServer::register(sd) {
        Ok(s) => s,
        Err(e) => {
            warn!("Failed to register RokiService: {}", defmt::Debug2Format(&e));
            return;
        }
    };

    // Spawn the advertising / reconnection loop as a background task
    // We use a `static` ref to pass to the task so it survives the loop.
    let server_ref: &'static RokiServer = {
        #[allow(static_mut_refs)]
        unsafe {
            static mut SERVER_STATIC: Option<RokiServer> = None;
            SERVER_STATIC = Some(server);
            SERVER_STATIC.as_ref().unwrap()
        }
    };

    embassy_futures::join::join(
        async {
            // ── Advertise + accept connections forever ──
            info!("Secondary link task starting");
            loop {
                let adv_data = AdvertisementBuilder::<31>::new()
                    .flags(&[Flag::GeneralDiscovery, Flag::LE_Only])
                    .services_128(ServiceList::Complete, &[ROKI_UUID_128])
                    .short_name("Roki")
                    .build();

                info!("Advertising RokiService...");
                let conn = match advertise_connectable(
                    sd,
                    ConnectableAdvertisement::ScannableUndirected {
                        adv_data: adv_data.as_ref(),
                        scan_data: &[],
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
                        warn!("Advertising failed: {}", defmt::Debug2Format(&e));
                        Timer::after(Duration::from_secs(5)).await;
                        continue;
                    }
                };

                PRIMARY_CONN.lock(|cell| {
                    *cell.borrow_mut() = Some(conn);
                });

                // Keep-alive: refresh the connection slot every 30 s so a
                // stale (silently dead) connection is dropped and we re-advertise.
                Timer::after(Duration::from_secs(30)).await;
                info!("Primary slot refresh — clearing stale connection");
                PRIMARY_CONN.lock(|cell| {
                    *cell.borrow_mut() = None;
                });
            }
        },
        async {
            // ── Main loop: read inputs and notify primary ──
            let mut counter = Cycle::new(0, 100);
            let layer = LayerHandler::<8>::new();
            let mut send_thumb = false;

            loop {
                if let Ok(event) = key_rx.try_receive() {
                    let current_layer = config.layers.get(layer.current()).unwrap();
                    let key = current_layer.secondary_keys[event.index as usize];

                    if event.pressed {
                        if let KeyAction::Layer(LayerCommand::ToggleExtras) = key {
                            let extras = EXTRAS.load(Ordering::Relaxed);
                            EXTRAS.store(!extras, Ordering::Relaxed);
                        }
                    }

                    if !matches!(key, KeyAction::Layer(_)) {
                        counter.increment();
                        let packet = protocol::pack_packet(
                            counter.value(),
                            protocol::KEY,
                            (event.index, event.pressed as u8),
                        );
                        PRIMARY_CONN.lock(|cell| {
                            if let Some(ref conn) = *cell.borrow() {
                                server_ref.notify(conn, &packet);
                            }
                        });
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
                    PRIMARY_CONN.lock(|cell| {
                        if let Some(ref conn) = *cell.borrow() {
                            server_ref.notify(conn, &packet);
                        }
                    });
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
                        PRIMARY_CONN.lock(|cell| {
                            if let Some(ref conn) = *cell.borrow() {
                                server_ref.notify(conn, &packet);
                            }
                        });
                        trace!("TX THUMB packet: {:?}", packet);
                        send_thumb = true;
                    } else if send_thumb {
                        let packet = protocol::pack_packet(counter.value(), protocol::THUMB_STICK, (0, 0));
                        PRIMARY_CONN.lock(|cell| {
                            if let Some(ref conn) = *cell.borrow() {
                                server_ref.notify(conn, &packet);
                            }
                        });
                        trace!("TX THUMB zero packet: {:?}", packet);
                        send_thumb = false;
                    }
                }

                Timer::after(Duration::from_micros(500)).await;
            }
        },
    )
    .await;
}
