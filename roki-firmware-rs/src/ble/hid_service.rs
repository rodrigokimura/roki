/// HID over GATT Profile (HOGP) service definitions.
///
/// Defines the HID Service (0x1812) with:
///   - HID Information (0x2A4A)
///   - Report Map (0x2A4B)
///   - HID Control Point (0x2A4C)
///   - Protocol Mode (0x2A4E)
///   - Input Report (0x2A4D) for keyboard, mouse, consumer
///
/// This is the minimum viable HOGP for keyboard + mouse + consumer media.
///
/// TODO: Full GATT server registration via nrf-softdevice macro or
/// raw SoftDevice calls. This module currently contains the descriptor
/// and report structures; the actual GATT registration happens in the
/// primary task when it starts advertising.

/// HID Report IDs used by our descriptor.
pub const RID_KEYBOARD: u8 = 1;
pub const RID_MOUSE: u8 = 2;
pub const RID_CONSUMER: u8 = 3;

/// Combined HID Report Map descriptor for keyboard + mouse + consumer.
///
/// Layout:
///   - Report ID 1: Boot-compatible keyboard (8 bytes)
///   - Report ID 2: Mouse (4 bytes: buttons, X, Y, wheel)
///   - Report ID 3: Consumer control (2 bytes: usage)
///
/// This is a byte-for-byte descriptor that Windows, macOS, and Linux
/// all parse correctly for a multi-report HID device.
pub const REPORT_MAP: &[u8] = &[
    // ── Keyboard (Report ID 1) ──────────────────────────
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
    0x81, 0x02,       // Input (Data, Variable, Absolute) — Modifier byte
    0x95, 0x01,       // Report Count (1)
    0x75, 0x08,       // Report Size (8)
    0x81, 0x01,       // Input (Constant) — Reserved byte
    0x95, 0x05,       // Report Count (5)
    0x75, 0x01,       // Report Size (1)
    0x05, 0x08,       // Usage Page (LEDs)
    0x19, 0x01,       // Usage Minimum (1)
    0x29, 0x05,       // Usage Maximum (5)
    0x91, 0x02,       // Output (Data, Variable, Absolute) — LED report
    0x95, 0x01,       // Report Count (1)
    0x75, 0x03,       // Report Size (3)
    0x91, 0x01,       // Output (Constant)
    0x95, 0x06,       // Report Count (6)
    0x75, 0x08,       // Report Size (8)
    0x15, 0x00,       // Logical Minimum (0)
    0x25, 0xFF,       // Logical Maximum (255)
    0x05, 0x07,       // Usage Page (Key Codes)
    0x19, 0x00,       // Usage Minimum (0)
    0x29, 0xFF,       // Usage Maximum (255)
    0x81, 0x00,       // Input (Data, Array) — 6 keycodes
    0xC0,             // End Collection

    // ── Mouse (Report ID 2) ─────────────────────────────
    0x05, 0x01,       // Usage Page (Generic Desktop)
    0x09, 0x02,       // Usage (Mouse)
    0xA1, 0x01,       // Collection (Application)
    0x85, RID_MOUSE,  // Report ID (2)
    0x09, 0x01,       // Usage (Pointer)
    0xA1, 0x00,       // Collection (Physical)
    0x05, 0x09,       // Usage Page (Button)
    0x19, 0x01,       // Usage Minimum (1)
    0x29, 0x03,       // Usage Maximum (3)
    0x15, 0x00,       // Logical Minimum (0)
    0x25, 0x01,       // Logical Maximum (1)
    0x75, 0x01,       // Report Size (1)
    0x95, 0x03,       // Report Count (3)
    0x81, 0x02,       // Input (Data, Variable, Absolute) — Buttons
    0x95, 0x01,       // Report Count (1)
    0x75, 0x05,       // Report Size (5)
    0x81, 0x01,       // Input (Constant) — Padding
    0x05, 0x01,       // Usage Page (Generic Desktop)
    0x09, 0x30,       // Usage (X)
    0x09, 0x31,       // Usage (Y)
    0x15, 0x81,       // Logical Minimum (-127)
    0x25, 0x7F,       // Logical Maximum (127)
    0x75, 0x08,       // Report Size (8)
    0x95, 0x02,       // Report Count (2)
    0x81, 0x06,       // Input (Data, Variable, Relative) — X, Y
    0x09, 0x38,       // Usage (Wheel)
    0x15, 0x81,       // Logical Minimum (-127)
    0x25, 0x7F,       // Logical Maximum (127)
    0x75, 0x08,       // Report Size (8)
    0x95, 0x01,       // Report Count (1)
    0x81, 0x06,       // Input (Data, Variable, Relative) — Wheel
    0xC0,             // End Collection (Physical)
    0xC0,             // End Collection (Application)

    // ── Consumer Control (Report ID 3) ──────────────────
    0x05, 0x0C,       // Usage Page (Consumer Devices)
    0x09, 0x01,       // Usage (Consumer Control)
    0xA1, 0x01,       // Collection (Application)
    0x85, RID_CONSUMER, // Report ID (3)
    0x19, 0x00,       // Usage Minimum (0)
    0x2A, 0x3C, 0x02, // Usage Maximum (0x023C)
    0x15, 0x00,       // Logical Minimum (0)
    0x26, 0x3C, 0x02, // Logical Maximum (0x023C)
    0x75, 0x10,       // Report Size (16)
    0x95, 0x01,       // Report Count (1)
    0x81, 0x00,       // Input (Data, Array) — Consumer usage
    0xC0,             // End Collection
];

/// HID Information characteristic value.
/// bcdHID=1.11, bCountryCode=0, flags=RemoteWake|NormallyConnectable
pub const HID_INFORMATION: [u8; 4] = [0x11, 0x01, 0x00, 0x03];

/// Report structure sent to the host.
/// The first byte is always the Report ID when using multiple reports.
#[derive(Clone, Copy, Debug)]
pub struct HidInputReport {
    pub report_id: u8,
    pub data: [u8; 8],
    pub len: usize,
}

impl HidInputReport {
    pub const fn keyboard(modifiers: u8, keys: [u8; 6]) -> Self {
        Self {
            report_id: RID_KEYBOARD,
            data: [modifiers, 0x00, keys[0], keys[1], keys[2], keys[3], keys[4], keys[5]],
            len: 8,
        }
    }

    pub const fn mouse(buttons: u8, x: i8, y: i8, wheel: i8) -> Self {
        Self {
            report_id: RID_MOUSE,
            data: [buttons, x as u8, y as u8, wheel as u8, 0, 0, 0, 0],
            len: 4,
        }
    }

    pub const fn consumer(usage: u16) -> Self {
        Self {
            report_id: RID_CONSUMER,
            data: [usage as u8, (usage >> 8) as u8, 0, 0, 0, 0, 0, 0],
            len: 2,
        }
    }

    pub fn as_bytes(&self) -> &[u8] {
        &self.data[..self.len]
    }
}
