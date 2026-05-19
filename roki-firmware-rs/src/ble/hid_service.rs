/// HID over GATT Profile (HOGP) — full GATT server registration.
///
/// Registers the HID Service (0x1812) with input reports for keyboard,
/// mouse, and consumer controls. The primary side (left half) advertises
/// this service to the host OS.

use nrf_softdevice::ble::gatt_server::builder::ServiceBuilder;
use nrf_softdevice::ble::gatt_server::characteristic::{Attribute, Metadata, Properties};
use nrf_softdevice::ble::gatt_server::CharacteristicHandles;
use nrf_softdevice::ble::{Connection, Uuid};
use nrf_softdevice::Softdevice;

use crate::logging::info;

// ── UUID helpers ───────────────────────────────────────────────────────

const fn uuid_16(v: u16) -> Uuid {
    Uuid::new_16(v)
}

// ── HID Report IDs ─────────────────────────────────────────────────────

pub const RID_KEYBOARD: u8 = 1;
pub const RID_MOUSE: u8 = 2;
pub const RID_CONSUMER: u8 = 3;

// ── Report Map ─────────────────────────────────────────────────────────

pub const REPORT_MAP: &[u8] = &[
    // Keyboard (Report ID 1)
    0x05, 0x01,       // Usage Page (Generic Desktop)
    0x09, 0x06,       // Usage (Keyboard)
    0xA1, 0x01,       // Collection (Application)
    0x85, RID_KEYBOARD, // Report ID (1)
    0x05, 0x07,       // Usage Page (Key Codes)
    0x19, 0xE0,       // Usage Minimum (224)
    0x29, 0xE7,       // Usage Maximum (231)
    0x15, 0x00,       // Logical Minimum (0)
    0x25, 0x01,       // Logical Maximum (1)
    0x75, 0x01,       // Report Size (1)
    0x95, 0x08,       // Report Count (8)
    0x81, 0x02,       // Input — Modifier byte
    0x95, 0x01,
    0x75, 0x08,
    0x81, 0x01,       // Input (Constant) — Reserved
    0x95, 0x05,
    0x75, 0x01,
    0x05, 0x08,       // Usage Page (LEDs)
    0x19, 0x01,
    0x29, 0x05,
    0x91, 0x02,       // Output — LED report
    0x95, 0x01,
    0x75, 0x03,
    0x91, 0x01,       // Output (Constant)
    0x95, 0x06,
    0x75, 0x08,
    0x15, 0x00,
    0x25, 0xFF,
    0x05, 0x07,
    0x19, 0x00,
    0x29, 0xFF,
    0x81, 0x00,       // Input — 6 keycodes
    0xC0,             // End Collection

    // Mouse (Report ID 2)
    0x05, 0x01,
    0x09, 0x02,       // Usage (Mouse)
    0xA1, 0x01,       // Collection (Application)
    0x85, RID_MOUSE,  // Report ID (2)
    0x09, 0x01,
    0xA1, 0x00,       // Collection (Physical)
    0x05, 0x09,
    0x19, 0x01,
    0x29, 0x03,
    0x15, 0x00,
    0x25, 0x01,
    0x75, 0x01,
    0x95, 0x03,
    0x81, 0x02,       // Input — Buttons
    0x95, 0x01,
    0x75, 0x05,
    0x81, 0x01,       // Input (Constant)
    0x05, 0x01,
    0x09, 0x30,       // Usage (X)
    0x09, 0x31,       // Usage (Y)
    0x15, 0x81,
    0x25, 0x7F,
    0x75, 0x08,
    0x95, 0x02,
    0x81, 0x06,       // Input — X, Y
    0x09, 0x38,       // Usage (Wheel)
    0x15, 0x81,
    0x25, 0x7F,
    0x75, 0x08,
    0x95, 0x01,
    0x81, 0x06,       // Input — Wheel
    0xC0,
    0xC0,

    // Consumer (Report ID 3)
    0x05, 0x0C,       // Usage Page (Consumer Devices)
    0x09, 0x01,
    0xA1, 0x01,       // Collection (Application)
    0x85, RID_CONSUMER, // Report ID (3)
    0x19, 0x00,
    0x2A, 0x3C, 0x02, // Usage Maximum (0x023C)
    0x15, 0x00,
    0x26, 0x3C, 0x02,
    0x75, 0x10,       // Report Size (16)
    0x95, 0x01,
    0x81, 0x00,       // Input — Consumer usage
    0xC0,
];

/// HID Information: bcdHID=1.11, bCountryCode=0, flags=RemoteWake|NormallyConnectable
const HID_INFORMATION: [u8; 4] = [0x11, 0x01, 0x00, 0x03];

// ── GATT Server handles ────────────────────────────────────────────────

pub struct HidServer {
    pub report_map: CharacteristicHandles,
    pub keyboard_input: CharacteristicHandles,
    pub mouse_input: CharacteristicHandles,
    pub consumer_input: CharacteristicHandles,
    pub hid_info: CharacteristicHandles,
    pub protocol_mode: CharacteristicHandles,
    pub control_point: CharacteristicHandles,
}

impl HidServer {
    pub fn register(sd: &mut Softdevice) -> Result<Self, nrf_softdevice::ble::gatt_server::RegisterError> {
        let mut sb = ServiceBuilder::new(sd, uuid_16(0x1812))?;

        // HID Information (read-only)
        let hid_info_c = sb.add_characteristic(
            uuid_16(0x2A4A),
            Attribute::new(&HID_INFORMATION).security(nrf_softdevice::ble::SecurityMode::JustWorks),
            Metadata::new(Properties::new().read()),
        )?;
        let hid_info = hid_info_c.build();

        // Report Map (read-only)
        let report_map_c = sb.add_characteristic(
            uuid_16(0x2A4B),
            Attribute::new(REPORT_MAP).security(nrf_softdevice::ble::SecurityMode::JustWorks),
            Metadata::new(Properties::new().read()),
        )?;
        let report_map = report_map_c.build();

        // Protocol Mode (read/write, default report protocol)
        const PROTOCOL_MODE: [u8; 1] = [0x01]; // 1 = Report Protocol
        let protocol_c = sb.add_characteristic(
            uuid_16(0x2A4E),
            Attribute::new(&PROTOCOL_MODE).security(nrf_softdevice::ble::SecurityMode::JustWorks),
            Metadata::new(Properties::new().read().write_without_response()),
        )?;
        let protocol_mode = protocol_c.build();

        // HID Control Point (write-only)
        let control_c = sb.add_characteristic(
            uuid_16(0x2A4C),
            Attribute::new(&[0u8; 1]).security(nrf_softdevice::ble::SecurityMode::JustWorks),
            Metadata::new(Properties::new().write_without_response()),
        )?;
        let control_point = control_c.build();

        // --- Input Reports: each with Report Reference descriptor ---

        // Keyboard Input Report (notify)
        let mut kb_c = sb.add_characteristic(
            uuid_16(0x2A4D),
            Attribute::new(&[0u8; 8]).variable_len(8)
                .security(nrf_softdevice::ble::SecurityMode::JustWorks),
            Metadata::new(Properties::new().read().notify()),
        )?;
        let kb_ref = [RID_KEYBOARD, 0x01]; // [report_id, input=1]
        kb_c.add_descriptor(
            uuid_16(0x2908),
            Attribute::new(&kb_ref).security(nrf_softdevice::ble::SecurityMode::JustWorks),
        )?;
        let keyboard_input = kb_c.build();

        // Mouse Input Report (notify)
        let mut mouse_c = sb.add_characteristic(
            uuid_16(0x2A4D),
            Attribute::new(&[0u8; 4]).variable_len(4)
                .security(nrf_softdevice::ble::SecurityMode::JustWorks),
            Metadata::new(Properties::new().read().notify()),
        )?;
        let mouse_ref = [RID_MOUSE, 0x01];
        mouse_c.add_descriptor(
            uuid_16(0x2908),
            Attribute::new(&mouse_ref).security(nrf_softdevice::ble::SecurityMode::JustWorks),
        )?;
        let mouse_input = mouse_c.build();

        // Consumer Input Report (notify)
        let mut cons_c = sb.add_characteristic(
            uuid_16(0x2A4D),
            Attribute::new(&[0u8; 2]).variable_len(2)
                .security(nrf_softdevice::ble::SecurityMode::JustWorks),
            Metadata::new(Properties::new().read().notify()),
        )?;
        let cons_ref = [RID_CONSUMER, 0x01];
        cons_c.add_descriptor(
            uuid_16(0x2908),
            Attribute::new(&cons_ref).security(nrf_softdevice::ble::SecurityMode::JustWorks),
        )?;
        let consumer_input = cons_c.build();

        let _ = sb.build();
        info!("HID service registered");

        Ok(Self {
            report_map,
            keyboard_input,
            mouse_input,
            consumer_input,
            hid_info,
            protocol_mode,
            control_point,
        })
    }

    /// Send a keyboard report (Report ID 1) to the host.
    pub fn send_keyboard(&self, conn: &Connection, modifiers: u8, keys: [u8; 6]) {
        let report = [modifiers, 0x00, keys[0], keys[1], keys[2], keys[3], keys[4], keys[5]];
        let _ = nrf_softdevice::ble::gatt_server::notify_value(
            conn,
            self.keyboard_input.value_handle,
            &report,
        );
    }

    /// Send a mouse report (Report ID 2) to the host.
    pub fn send_mouse(&self, conn: &Connection, buttons: u8, x: i8, y: i8, wheel: i8) {
        let report = [buttons, x as u8, y as u8, wheel as u8];
        let _ = nrf_softdevice::ble::gatt_server::notify_value(
            conn,
            self.mouse_input.value_handle,
            &report,
        );
    }

    /// Send a consumer/media report (Report ID 3) to the host.
    pub fn send_consumer(&self, conn: &Connection, usage: u16) {
        let report = [usage as u8, (usage >> 8) as u8];
        let _ = nrf_softdevice::ble::gatt_server::notify_value(
            conn,
            self.consumer_input.value_handle,
            &report,
        );
    }
}

// ── HID Output Report (received from host) ─────────────────────────────

/// LED state received from host (bit 0=NumLock, 1=CapsLock, 2=ScrollLock).
#[derive(Clone, Copy, Debug, Default)]
pub struct LedState {
    pub num_lock: bool,
    pub caps_lock: bool,
    pub scroll_lock: bool,
}

impl LedState {
    pub fn from_byte(b: u8) -> Self {
        Self {
            num_lock: b & 0x01 != 0,
            caps_lock: b & 0x02 != 0,
            scroll_lock: b & 0x04 != 0,
        }
    }
}
