/// Custom BLE GATT service for inter-half keyboard communication.
///
/// - Secondary side: `RokiServer` registers the service and notifies packets.
/// - Primary side: `RokiClient` discovers the service and receives notifications.

use nrf_softdevice::ble::gatt_server::builder::ServiceBuilder;
use nrf_softdevice::ble::gatt_server::characteristic::{Attribute, Metadata, Properties};
use nrf_softdevice::ble::gatt_server::CharacteristicHandles;
use nrf_softdevice::ble::{Connection, Uuid};
use nrf_softdevice::Softdevice;

// ── UUIDs ──────────────────────────────────────────────────────────────

fn make_uuid_16(base: [u8; 16], idx: u16) -> Uuid {
    let mut u = base;
    u[12] = (idx & 0xFF) as u8;
    u[13] = (idx >> 8) as u8;
    Uuid::new_128(&u)
}

/// Base = "reffuBtekcaP\x00\x00\xaf\xad"
const BASE: [u8; 16] = *b"reffuBtekcaP\x00\x00\xaf\xad";

/// The full 128-bit UUID bytes for the RokiService (with service index 0x0001).
pub const ROKI_UUID_128: [u8; 16] = {
    let mut u = BASE;
    u[12] = 0x01;
    u[13] = 0x00;
    u
};

fn roki_service_uuid() -> Uuid {
    Uuid::new_128(&ROKI_UUID_128)
}

fn roki_char_packets_uuid() -> Uuid {
    make_uuid_16(BASE, 0x0101)
}

// ── GATT Server (secondary side) ──────────────────────────────────────

/// Handle for the registered RokiService on the GATT server.
pub struct RokiServer {
    pub packets: CharacteristicHandles,
}

impl RokiServer {
    /// Register the RokiService on the SoftDevice GATT server.
    pub fn register(sd: &mut Softdevice) -> Result<Self, nrf_softdevice::ble::gatt_server::RegisterError> {
        let mut sb = ServiceBuilder::new(sd, roki_service_uuid())?;
        let cb = sb.add_characteristic(
            roki_char_packets_uuid(),
            Attribute::new(&[0u8; 4]).variable_len(4),
            Metadata::new(
                Properties::new()
                    .read()
                    .write_without_response()
                    .notify(),
            ),
        )?;
        let handles = cb.build();
        let _ = sb.build();
        Ok(Self {
            packets: handles,
        })
    }

    /// Send a 4-byte packet notification to the connected primary.
    #[inline]
    pub fn notify(&self, conn: &Connection, data: &[u8; 4]) {
        let _ = nrf_softdevice::ble::gatt_server::notify_value(
            conn,
            self.packets.value_handle,
            data,
        );
    }
}

// ── GATT Client (primary side) ────────────────────────────────────────

use nrf_softdevice::ble::gatt_client::{self, Characteristic, Descriptor};

/// Client-side view of the RokiService discovered on the secondary half.
pub struct RokiClient {
    /// Characteristic value handle for the packet buffer.
    pub packets_value_handle: Option<u16>,
    /// CCCD handle for enabling notifications.
    pub packets_cccd_handle: Option<u16>,
}

impl RokiClient {
    pub const fn new() -> Self {
        Self {
            packets_value_handle: None,
            packets_cccd_handle: None,
        }
    }

    /// Once handles are known, enable notifications by writing 0x0001 to the CCCD.
    pub async fn enable_notifications(&self, conn: &Connection) -> Result<(), nrf_softdevice::ble::gatt_client::WriteError> {
        if let Some(cccd) = self.packets_cccd_handle {
            gatt_client::write_without_response(conn, cccd, &[0x01, 0x00]).await?;
        }
        Ok(())
    }
}

impl nrf_softdevice::ble::gatt_client::Client for RokiClient {
    type Event = RokiClientEvent;

    fn on_hvx(
        &self,
        _conn: &Connection,
        _type: nrf_softdevice::ble::gatt_client::HvxType,
        handle: u16,
        data: &[u8],
    ) -> Option<Self::Event> {
        if self.packets_value_handle == Some(handle) && data.len() == 4 {
            Some(RokiClientEvent::Packet(data.try_into().ok()?))
        } else {
            None
        }
    }

    fn uuid() -> Uuid {
        roki_service_uuid()
    }

    fn new_undiscovered(_conn: Connection) -> Self {
        Self::new()
    }

    fn discovered_characteristic(
        &mut self,
        characteristic: &Characteristic,
        descriptors: &[Descriptor],
    ) {
        if characteristic.uuid == Some(roki_char_packets_uuid()) {
            self.packets_value_handle = Some(characteristic.handle_value);
            for desc in descriptors {
                if desc.uuid == Some(Uuid::new_16(0x2902)) {
                    self.packets_cccd_handle = Some(desc.handle);
                }
            }
        }
    }

    fn discovery_complete(&mut self) -> Result<(), nrf_softdevice::ble::gatt_client::DiscoverError> {
        if self.packets_value_handle.is_some() {
            Ok(())
        } else {
            Err(nrf_softdevice::ble::gatt_client::DiscoverError::ServiceIncomplete)
        }
    }
}

/// Events emitted by the Roki GATT client when receiving notifications.
#[derive(Clone, Copy, Debug)]
pub enum RokiClientEvent {
    /// A 4-byte inter-half packet arrived.
    Packet([u8; 4]),
}
