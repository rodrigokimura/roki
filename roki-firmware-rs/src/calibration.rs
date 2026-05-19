use embedded_storage::nor_flash::NorFlash;
use serde::{Deserialize, Serialize};

use crate::logging::{debug, info};

/// ── Calibration data persisted in flash ────────────────────────────────
///
/// Stored as postcard-encoded bytes in a dedicated flash page.
/// The nRF52840 has 1024 pages of 4096 bytes. We target an address
/// near the end of flash to avoid colliding with the bootloader or
/// application code.
///
/// TODO: make this configurable based on SoftDevice size + app size.
const CALIBRATION_PAGE: u32 = 0xF9000; // Page 249 of 0x100000 (1 MB flash)
const FLASH_PAGE_SIZE: usize = 4096;

#[derive(Clone, Copy, Debug, Serialize, Deserialize, Default)]
pub struct CalibrationData {
    pub min_x: i16,
    pub mid_x: i16,
    pub max_x: i16,
    pub min_y: i16,
    pub mid_y: i16,
    pub max_y: i16,
}

impl CalibrationData {
    /// Read calibration from flash. Returns `None` if the page is
    /// unwritten (all 0xFF) or the data is corrupt.
    pub fn load() -> Option<Self> {
        let raw = unsafe {
            core::slice::from_raw_parts(CALIBRATION_PAGE as *const u8, FLASH_PAGE_SIZE)
        };

        // Quick check: if the first byte is 0xFF the page is erased.
        if raw[0] == 0xFF {
            return None;
        }

        match postcard::from_bytes(raw) {
            Ok(data) => {
                info!("Loaded calibration from flash");
                Some(data)
            }
            Err(e) => {
                debug!("Calibration flash decode error: {:?}", e);
                None
            }
        }
    }

    /// Write calibration to a dedicated flash page.
    /// This blocks while the NVMC does its erase + write cycle.
    pub fn save_to_flash(&self) {
        let mut nvmc = embassy_nrf::nvmc::Nvmc::new(
            unsafe { embassy_nrf::peripherals::NVMC::steal() }
        );
        self.save(&mut nvmc);
    }

    pub fn save(&self, nvmc: &mut embassy_nrf::nvmc::Nvmc<'_>) {
        let mut buf = [0u8; 128];
        let encoded = match postcard::to_slice(self, &mut buf) {
            Ok(b) => b,
            Err(_) => {
                debug!("Failed to serialize calibration");
                return;
            }
        };

        // Erase the page first (Nordic flash requires page-erase before write)
        let _ = nvmc.erase(CALIBRATION_PAGE, CALIBRATION_PAGE + FLASH_PAGE_SIZE as u32);

        // Write the data
        let _ = nvmc.write(CALIBRATION_PAGE, encoded);

        info!("Calibration saved to flash ({} bytes)", encoded.len());
    }
}

/// Runtime-calculated normalization boundaries derived from `CalibrationData`.
///
/// These are the same fields computed in `BaseCalibration._get_normalized_x/y`
/// in the Python firmware, but precomputed once at boot.
#[derive(Clone, Debug)]
pub struct NormalizedCalibration {
    pub lower_mid_x: i16,
    pub upper_mid_x: i16,
    pub min_x: i16,
    pub max_x: i16,
    pub lower_mid_y: i16,
    pub upper_mid_y: i16,
    pub min_y: i16,
    pub max_y: i16,
    _limit: f32,
}

impl NormalizedCalibration {
    pub fn from_data(data: &CalibrationData) -> Self {
        let limit = 0.05f32;
        Self {
            min_x: data.min_x,
            max_x: data.max_x,
            lower_mid_x: data.mid_x - ((data.mid_x - data.min_x) as f32 * limit) as i16,
            upper_mid_x: data.mid_x + ((data.max_x - data.mid_x) as f32 * limit) as i16,
            min_y: data.min_y,
            max_y: data.max_y,
            lower_mid_y: data.mid_y - ((data.mid_y - data.min_y) as f32 * limit) as i16,
            upper_mid_y: data.mid_y + ((data.max_y - data.mid_y) as f32 * limit) as i16,
            _limit: limit,
        }
    }

    /// Normalize a raw X ADC reading to `[-1.0, 1.0]`.
    #[inline]
    pub fn normalize_x(&self, raw: i16) -> f32 {
        if raw < self.lower_mid_x {
            -((self.lower_mid_x - raw) as f32 / (self.lower_mid_x - self.min_x) as f32)
                .clamp(0.0, 1.0)
        } else if raw > self.upper_mid_x {
            ((raw - self.upper_mid_x) as f32 / (self.max_x - self.upper_mid_x) as f32)
                .clamp(0.0, 1.0)
        } else {
            0.0
        }
    }

    /// Normalize a raw Y ADC reading to `[-1.0, 1.0]`.
    #[inline]
    pub fn normalize_y(&self, raw: i16) -> f32 {
        if raw < self.lower_mid_y {
            -((self.lower_mid_y - raw) as f32 / (self.lower_mid_y - self.min_y) as f32)
                .clamp(0.0, 1.0)
        } else if raw > self.upper_mid_y {
            ((raw - self.upper_mid_y) as f32 / (self.max_y - self.upper_mid_y) as f32)
                .clamp(0.0, 1.0)
        } else {
            0.0
        }
    }
}

/// Run-time calibration procedure.
///
/// 1. If thumbstick switch is not held at boot, skip calibration.
/// 2. Play start tone, wait 5 s for user to release switch.
/// 3. Sample center (mid) values for 5 s while user holds stick neutral.
/// 4. Play rotation tone, sample min/max while user rotates stick to edges.
/// 5. Stop when switch is pressed again.
/// 6. Save to flash.
///
/// TODO: wire this into `thumbstick_task` or a dedicated calibration boot task.
pub struct Calibrator {
    data: CalibrationData,
}

impl Calibrator {
    pub const fn new() -> Self {
        Self {
            data: CalibrationData {
                min_x: i16::MAX,
                mid_x: 0,
                max_x: i16::MIN,
                min_y: i16::MAX,
                mid_y: 0,
                max_y: i16::MIN,
            },
        }
    }

    pub fn reset(&mut self) {
        self.data = CalibrationData::default();
        self.data.min_x = i16::MAX;
        self.data.max_x = i16::MIN;
        self.data.min_y = i16::MAX;
        self.data.max_y = i16::MIN;
    }

    pub fn sample_center(&mut self, x: i16, y: i16) {
        // Running average would be better; for now just keep latest
        // since user is supposed to hold perfectly still.
        self.data.mid_x = x;
        self.data.mid_y = y;
    }

    pub fn sample_extents(&mut self, x: i16, y: i16) {
        self.data.min_x = self.data.min_x.min(x);
        self.data.max_x = self.data.max_x.max(x);
        self.data.min_y = self.data.min_y.min(y);
        self.data.max_y = self.data.max_y.max(y);
    }

    pub fn data(&self) -> &CalibrationData {
        &self.data
    }
}
