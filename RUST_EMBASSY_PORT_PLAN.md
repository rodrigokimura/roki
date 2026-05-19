# RoKi Firmware Port Plan: CircuitPython → Rust + Embassy

> Branch: `plan/rust-embassy-port`  
> Target platform: nice!nano v2 (nRF52840, BLE)  
> Status: M0 complete — project compiles; modules scaffolded; warnings cleanup in progress

---

## 1. Motivation

**Current stack:** CircuitPython on nice!nano v2.

**Problems to solve with Rust + Embassy:**
- **Startup latency:** CircuitPython interpreter adds ~300–500 ms before the main loop runs.
- **Memory pressure:** nRF52840 has 256 KB RAM; the CP heap is tiny. Large keymaps and HID descriptors fight for space.
- **No real concurrency:** CP code is synchronous and event polling is manually interleaved.
- **Build reproducibility:** A Rust crate + `cargo build` is far more hermetic than hand-copied `.mpy` bundles.
- **BLE HID stack:** `adafruit_ble` + `adafruit_hid` are convenient but opaque and slow to evolve. Embassy + SoftDevice gives us the same Nordic silicon primitives the keyboard community uses in QMK/ZMK.

---

## 2. Target Crate Stack

```toml
[dependencies]
# ── Async runtime ──────────────────────────────────
embassy-executor = { version = "0.6", features = ["arch-cortex-m", "executor-thread"] }
embassy-time     = { version = "0.3", features = ["driver-timer-nrf"] }
embassy-sync     = "0.6"
embassy-futures  = "0.1"

# ── nRF52840 HAL ───────────────────────────────────
embassy-nrf = { version = "0.2", features = [
    "nrf52840",
    "time-driver-rtc1",
    "gpiote",
    "unstable-pac",
] }

# ── BLE (SoftDevice s140) ──────────────────────────
nrf-softdevice      = { version = "0.1", features = ["s140", "nrf52840", "ble-peripheral", "ble-central", "ble-gatt-server", "ble-gatt-client"] }
nrf-softdevice-s140 = "7.3"

# ── USB HID fallback ───────────────────────────────
embassy-usb = { version = "0.3", features = ["usbd-hid"] }
usbd-hid    = "0.8"

# ── No-std utilities ───────────────────────────────
heapless        = "0.8"   # Vec/String with fixed capacity
postcard        = "1.0"   # Compact serde (inter-half comms, flash storage)
serde           = { version = "1", default-features = false, features = ["derive"] }
serde-json-core = "0.6"  # Keymap JSON parse at boot

# ── Logging / debugging ────────────────────────────
defmt       = "0.3"
defmt-rtt   = "0.4"
panic-probe = { version = "0.3", features = ["print-defmt"] }

# ── Cortex-M runtime ───────────────────────────────
cortex-m    = "0.7"
cortex-m-rt = "0.7"

# Optional: consider `rumcake` (keyboard fw framework on embassy)
# rumcake = { git = "https://github.com/Univa/rumcake" }
```

---

## 3. File / Module Mapping

| Current (Python) | New (Rust) | Owner task | Notes |
|---|---|---|---|
| `code.py` | `src/main.rs` | `main()` / executor | Spawns all tasks, reads side switch |
| `boot.py` | `src/main.rs` + linker script | `pre_main()` | Replaced by compile-time config + flash-backed storage |
| `kb.py` → `Roki` | `src/keyboard.rs` | `Roki` struct | Composition over inheritance |
| `kb.py` → `Primary` | `src/side/primary.rs` | `primary_task()` | BLE central + HID host + matrix scan |
| `kb.py` → `Secondary` | `src/side/secondary.rs` | `secondary_task()` | BLE peripheral + custom GATT service + matrix scan |
| `keys.py` | `src/keymap/mod.rs` | Static dispatch | Keycode enum → HID report builders |
| `layer_handler.py` | `src/layers.rs` | Called from matrix task | State machine for tap/hold/toggle |
| `config.py` | `src/config.rs` + `config.json` | Compile-time / boot parse | `include_str!` default; flash override |
| `service.py` | `src/ble/roki_service.rs` | GATT server | Custom `RokiService` with PacketBuffer char |
| `buzzer.py` | `src/buzzer.rs` | `buzzer_task()` | PWM sequences, non-blocking |
| `calibration.py` | `src/calibration.rs` | `calibration_task()` | Flash page persistence via `nvmc` |
| `params.py` | `src/env.rs` | Static `const` / linker symbols | `IS_LEFT_SIDE`, `DEBUG`, `LOG_LEVEL` |
| `utils.py` | `src/utils.rs` | Various | `Cycle`, `Debouncer`, `Loop`, encode/decode helpers |
| `messages.py` | `src/protocol.rs` | Shared | `KEY`, `ENCODER`, `THUMB_STICK` constants |
| `logging.py` | `defmt` / `src/logging.rs` | Global | Drop-in structured logging via RTT |
| — (new) | `src/matrix.rs` | `matrix_task()` | GPIO row/column scan + debounce |
| — (new) | `src/encoder.rs` | `encoder_task()` | QDEC peripheral |
| — (new) | `src/thumbstick.rs` | `thumbstick_task()` | SAADC + normalization |
| — (new) | `src/ble/hid_service.rs` | Primary task | HOGP (HID over GATT Profile) |
| — (new) | `memory.x` | Linker | Flash / RAM layout for nRF52840 |
| — (new) | `build.rs` | Build script | Embed `config.json` / generate keycode tables |

---

## 4. Hardware Pin Mapping (nice!nano v2)

Extracted from `roki/firmware/code.py`:

| Function | Pin | Rust `peripherals::P0_*` | HAL module |
|---|---|---|---|
| Row 0 | P0.24 | `P0_24` | `gpio::Output` |
| Row 1 | P1.00 | `P1_00` | `gpio::Output` |
| Row 2 | P0.11 | `P0_11` | `gpio::Output` |
| Row 3 | P1.04 | `P1_04` | `gpio::Output` |
| Row 4 | P1.06 | `P1_06` | `gpio::Output` |
| Col 0 | P0.09 | `P0_09` | `gpio::Input` |
| Col 1 | P0.10 | `P0_10` | `gpio::Input` |
| Col 2 | P1.11 | `P1_11` | `gpio::Input` |
| Col 3 | `P1.13` | `P1_13` | `gpio::Input` |
| Col 4 | P1.15 | `P1_15` | `gpio::Input` |
| Col 5 | P0.02 | `P0_02` | `gpio::Input` |
| Buzzer | P0.06 | `P0_06` | `pwm::SimplePwm` |
| Thumb switch | P0.22 | `P0_22` | `gpio::Input` (`Pull::Up`) |
| Thumb X (ADC) | AIN7 → P0.31 | `P0_31` | `saadc::Channel` |
| Thumb Y (ADC) | AIN5 → P0.29 | `P0_29` | `saadc::Channel` |
| Encoder A | P0.17 | `P0_17` | `qdec` |
| Encoder B | P0.20 | `P0_20` | `qdec` |
| Onboard LED | P0.15 | `P0_15` (CHECK) | `gpio::Output` |

---

## 5. Architecture: Task Model

The CP `Roki.run_main_loop()` is a single thread that manually juggles BLE, matrix, encoder, and ADC. Embassy lets us run each subsystem as a real concurrent task.

```rust
#[embassy_executor::main]
async fn main(spawner: Spawner) {
    let p = embassy_nrf::init(Default::default());

    // Read side switch (or use linker/environment flag)
    let is_left = read_side_switch(&p); // P0.22 at boot

    // ── Shared channels ──────────────────────────
    static KEY_EVENTS:    Channel<NoopRawMutex, KeyEvent,     16> = Channel::new();
    static ENCODER_EVENTS: Channel<NoopRawMutex, EncoderEvent,  4> = Channel::new();
    static THUMB_EVENTS:  Channel<NoopRawMutex, ThumbEvent,    4> = Channel::new();

    // ── Spawn common tasks ───────────────────────
    spawner.must_spawn(matrix_task(/* row pins */, /* col pins */, KEY_EVENTS.sender()));
    spawner.must_spawn(encoder_task(p.P0_17, p.P0_20, ENCODER_EVENTS.sender()));
    spawner.must_spawn(thumbstick_task(p.SAADC, p.P0_31, p.P0_29, p.P0_22, THUMB_EVENTS.sender()));
    spawner.must_spawn(buzzer_task(p.P0_06));

    // ── Side-specific tasks ──────────────────────
    if is_left {
        spawner.must_spawn(primary_task(KEY_EVENTS.receiver(), ENCODER_EVENTS.receiver(), THUMB_EVENTS.receiver()));
    } else {
        spawner.must_spawn(secondary_task(KEY_EVENTS.receiver(), ENCODER_EVENTS.receiver(), THUMB_EVENTS.receiver()));
    }
}
```

### Task responsibilities

| Task | Priority | What it does | Yield points |
|---|---|---|---|
| `matrix_task` | High | Drives rows, reads columns, debounces | Every row (`Timer::after(5µs)`); every full scan (`Timer::after(1ms)`) |
| `encoder_task` | Medium | Reads `Qdec`, diffs position | Blocks on `qdec.read().await` |
| `thumbstick_task` | Low | Samples SAADC, applies calibration | `Timer::after(10ms).await` |
| `buzzer_task` | Low | Plays queued note sequences | `Timer::after(note_duration).await` |
| `primary_task` | High | BLE central scan → connect → advertise HID; dispatch HID reports; forward secondary events | `select!` on channel receivers + BLE events |
| `secondary_task` | High | BLE peripheral advertise; send matrix/encoder/stick events over custom GATT | Blocks on `advertise.start().await` + channels |

---

## 6. Module Details

### 6.1 `matrix.rs` — Key Matrix Scanner

CircuitPython's `keypad.KeyMatrix` does everything (scan + debounce + event queue). In Rust we rebuild it:

```rust
pub struct Matrix<const R: usize, const C: usize> {
    rows: [Output<'static>; R],
    cols: [Input<'static>; C],
    state: [[bool; C]; R],
    debounce: [[Option<Instant>; C]; R],
}
```

**Algorithm:**
1. For each row `r`: drive high, wait 5 µs, sample all columns.
2. If sample differs from `state[r][c]` and debounce timer is unset, start timer.
3. If timer elapsed > 5 ms, commit change and push `KeyEvent` to channel.

**Why not use `embassy-nrf` keypad support?** The nRF HAL doesn't have a built-in matrix helper. We keep it generic.

### 6.2 `encoder.rs` — Rotary Encoder via QDEC

```rust
let mut qdec = Qdec::new(p.QDEC, p.P0_17, p.P0_20, None, config);
let mut last = 0i32;
loop {
    let report = qdec.read().await;
    if let Some(acc) = report.acc() {
        let diff = acc - last;
        last = acc;
        if diff != 0 {
            tx.send(EncoderEvent { delta: diff as i8 }).await;
        }
    }
}
```

**Note:** The QDEC peripheral handles the pin-change interrupts internally; the task is mostly asleep.

### 6.3 `thumbstick.rs` — SAADC + Normalization

**ADC channels:** Two single-ended channels (X on P0.31, Y on P0.29) with `Gain::GAIN1_6` and internal reference.

**Calibration data structure (flash):**
```rust
#[repr(C)]
#[derive(Serialize, Deserialize, Clone, Copy)]
struct CalibrationData {
    min_x: i16, mid_x: i16, max_x: i16,
    min_y: i16, mid_y: i16, max_y: i16,
}
```

**Normalization (from `calibration.py`):**
```rust
fn normalize_x(&self, raw: i16) -> f32 {
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
```

**Calibration trigger at boot:** If thumbstick switch (`P0.22`) is held low during startup, enter calibration mode: buzzer plays start tone, wait 5 s for release, sample mid values for 5 s, then sample min/max while user rotates stick until switch is pressed again. Write result to flash page.

### 6.4 `side/primary.rs` — Left Side (HID Host + BLE Central)

**Startup sequence:**
1. Initialize SoftDevice + BLE radio.
2. Scan for `RokiService` advertisement from the right half.
3. Connect to secondary; negotiate connection interval (7.5 ms).
4. Start advertising as HID device with appearance = 961 (Keyboard).
5. Play "peripheral connected" sequence on buzzer.
6. Enter main loop.

**Main loop (via `select!`):**
```rust
loop {
    select! {
        event = key_rx.recv()     => process_primary_key(event),
        event = encoder_rx.recv() => process_primary_encoder(event),
        event = thumb_rx.recv()   => process_primary_thumbstick(event),
        packet = secondary_packet => {
            // Buffer from RokiService.readinto()
            let (counter, msg_id, p1, p2) = decode_packet(packet);
            if counter != current_counter {
                current_counter = counter;
                match msg_id {
                    KEY => process_secondary_key(p1, p2 != 0),
                    ENCODER => process_secondary_encoder(p1, p2),
                    THUMB_STICK => process_secondary_thumbstick(decode_float(p1), decode_float(p2)),
                }
            }
        }
    }
}
```

**HID report dispatch:** Keyboard uses boot protocol report (8 bytes). Mouse is a separate HOGP report. Consumer/media keys use a third report.

### 6.5 `side/secondary.rs` — Right Side (BLE Peripheral)

**Behavior:**
1. Create `RokiService` GATT server.
2. Advertise `ProvideServicesAdvertisement(RokiService)`.
3. Wait for primary to connect.
4. In main loop, read matrix/encoder/thumbstick events and send 4-byte packets over `RokiService.packets` characteristic (`write_without_response`).

**Packet format (compatible with current Python):**
```
[0] counter: u8   — monotonic, wraps at 100
[1] msg_id:  u8   — 1=KEY, 2=ENCODER, 3=THUMB_STICK
[2] payload_1: u8 — abs(value) or key_index
[3] payload_2: u8 — abs(value) or pressed_bool
```

**Extras toggle:** When the key at the secondary side mapped to `LAYER_EXTRAS` is pressed, flip a local `extras` flag. This flag gates whether encoder and thumbstick events are sent (same semantics as current `config.extras`).

### 6.6 `ble/roki_service.rs` — Custom GATT Service

```rust
#[nrf_softdevice::gatt_service(uuid = "PACKET_BUFFER_UUID")]
struct RokiService {
    #[characteristic(uuid = "0x0101", write_without_response, notify, read)]
    packets: [u8; 4],
}
```

**UUID derivation (from Python):**
```python
uuid128 = bytearray("reffuBtekcaP".encode("utf-8") + b"\x00\x00\xaf\xad")
```
This produces a VendorUUID with base `reffuBtekcaP\x00\x00\xaf\xad`. In Rust we use the same UUID bytes.

### 6.7 `ble/hid_service.rs` — HID over GATT (HOGP)

The biggest gap compared to CircuitPython. We must define:

- **Device Information Service** (`0x180A`) — manufacturer, software revision.
- **Battery Service** (`0x180F`) — optional but expected by hosts.
- **HID Service** (`0x1812`) with:
  - HID Information characteristic (`0x2A4A`)
  - Report Map characteristic (`0x2A4B`) — the descriptor
  - HID Control Point characteristic (`0x2A4C`)
  - Report characteristics (`0x2A4D`) — one for keyboard, one for mouse, one for consumer
  - Protocol Mode characteristic (`0x2A4E`) — boot protocol

**Report map** (combined keyboard + mouse + consumer):
We need a single descriptor or three separate reports. Current CP sends keyboard, mouse, and media via `adafruit_hid` which multiplexes onto one HID service. In HOGP the standard approach is three reports with distinct report IDs.

See [USB HID Usage Tables](https://www.usb.org/sites/default/files/documents/hut1_12v2.pdf) for the exact descriptor bytes.

### 6.8 `layers.rs` — Layer Handler

Port of `layer_handler.py`:

```rust
pub struct LayerHandler<const N: usize> {
    current: usize,
    previous: usize,
    pub extras: bool,
}

impl<const N: usize> LayerHandler<N> {
    pub fn on_press(&mut self, cmd: Command) { cmd.press(self); }
    pub fn on_release(&mut self, cmd: Command) { cmd.release(self); }
}

pub enum Command {
    LayerPress(usize),
    LayerHold(usize),
    LayerInc,
    LayerDec,
    ToggleExtras,
}
```

Key observation: `OnHoldCommand` returns to the previous layer on release. This is stateful but contained entirely within `LayerHandler`.

### 6.9 `keymap.rs` — Key Definitions + HID Report Builders

Port of the `BaseKey` hierarchy from `keys.py`:

```rust
pub enum KeyAction {
    Noop,
    Keyboard(u8),           // HID keycode
    Mouse(MouseAction),     // button or directional
    Media(u16),             // Consumer control code
    Layer(Command),         // layer switch command
}

pub enum MouseAction {
    Button(u8),
    MoveUp, MoveDown, MoveLeft, MoveRight,
    ScrollUp, ScrollDown,
}
```

The `Layer` struct from `config.py` becomes:
```rust
pub struct Layer {
    pub name: &'static str,
    pub color: (u8, u8, u8),
    pub primary_keys: [KeyAction; 30],      // 5×6
    pub secondary_keys: [KeyAction; 30],
    pub primary_encoder_cw: KeyAction,
    pub primary_encoder_ccw: KeyAction,
    pub secondary_encoder_cw: KeyAction,
    pub secondary_encoder_ccw: KeyAction,
}
```

### 6.10 `config.rs` — Compile-Time + Runtime Config

**Default keymap:** embedded via `include_str!("../config/default.json")` and parsed at boot with `serde-json-core`. If parsing fails, fall back to a hard-coded `const DEFAULT_LAYERS`.

**Runtime mutability:** The layer index and `extras` flag are mutable `static` (behind a `Mutex`). Calibration data is mutable flash.

**Boot-time side detection:**
- Option A: Compile two ELF files (`roki-left.elf`, `roki-right.elf`) with `IS_LEFT_SIDE` as a linker symbol. The CLI (`roki upload`) picks the right one.
- Option B: Read `P0_22` at boot (as `boot.py` does now) and branch. Simpler, keeps one binary.

**Recommendation:** Option B for now — read `P0_22` at startup before spawning tasks.

---

## 7. Data Flow: Primary Side

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│ Matrix task │────▶│ KeyEvents    │────▶│ Primary     │
│ (GPIO scan) │     │ channel      │     │ task        │
└─────────────┘     └──────────────┘     │             │
                                          │  • lookup   │
┌─────────────┐     ┌──────────────┐     │    layer    │
│ Encoder     │────▶│ EncoderEvents│────▶│  • build    │
│ task (QDEC) │     │ channel      │     │    HID      │
└─────────────┘     └──────────────┘     │    report   │
                                          │  • send to  │
┌─────────────┐     ┌──────────────┐     │    HOGP     │
│ Thumbstick  │────▶│ ThumbEvents  │────▶│             │
│ task (SAADC)│     │ channel      │     └──────┬──────┘
└─────────────┘     └──────────────┘            │
                                                ▼
┌─────────────────────────────────────────────────────────┐
│ Secondary half (BLE peripheral)                         │
│  RokiService.packets ──notify──▶ RokiService.readinto() │
│  └─ decoded into key/encoder/thumb events               │
│  └─ dispatched to same HID layer logic                  │
└─────────────────────────────────────────────────────────┘
```

---

## 8. Data Flow: Secondary Side

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌─────────┐
│ Matrix task │────▶│ KeyEvents    │────▶│ Secondary    │────▶│ RokiSvc │
│ (GPIO scan) │     │ channel      │     │ task         │     │ .write()│
└─────────────┘     └──────────────┘     │              │     └─────────┘
                                          │  • encode    │
┌─────────────┐     ┌──────────────┐     │  • send packet│
│ Encoder     │────▶│ EncoderEvents│────▶│              │
│ task (QDEC) │     │ channel      │     └──────────────┘
└─────────────┘     └──────────────┘
```

---

## 9. Storage Strategy (Replacing `config.json` + `calibration.json`)

CircuitPython has a FAT filesystem exposed over USB. Rust bare-metal does not.

| Data | Strategy | Persistence |
|---|---|---|
| Keymap | `include_str!("config/default.json")` → parsed at boot | Compile-time only |
| Calibration | `postcard` to flash page via `nvmc` | Boot-time read, calibration-write at runtime |
| Runtime state (layer index, extras) | In RAM (`static` + `Mutex`) | Lost on reset (acceptable) |
| Side selection | Read `P0_22` at boot, or compile flag | Deterministic at boot |

**Flash page for calibration:**
- nRF52840 has 1024 pages × 4096 bytes.
- SoftDevice s140 uses pages 0–N (check docs, usually ~160 KB, pages 0–39).
- Use the last safe page, e.g., address `0xED000` (page 237). Verify against SoftDevice size and application size.

---

## 10. Build / Flash Workflow

```bash
# 1. Build left/right firmware
cargo build --release --bin roki

# 2. Convert to UF2 (nice!nano ships with uf2 bootloader)
#   Use `elf2uf2-rs` or `objcopy` + community UF2 tool
elf2uf2-rs target/thumbv7em-none-eabihf/release/roki roki.uf2

# 3. Flash (mount as USB mass storage, or use probe-rs)
#   Double-tap reset → bootloader mode → copy UF2
cp roki.uf2 /media/NICENANO/

# 4. Debug logs via SWD / probe-rs
cargo run --release
#  → streams defmt RTT logs automatically via probe-rs
```

---

## 11. Host-Side Tooling (CP CLI → Rust? or Keep Python?)

The existing host tooling (`roki cli`, `roki tui`, `roki serve`) does:
- `upload` — copy files to CircuitPython USB drive
- `run` — TUI keymap editor
- `serve` — FastAPI web configurator
- `generate` — static HTML artifacts

**Decision:** Keep the Python CLI/TUI/web tools. They generate `config.json`, which we then embed in the Rust binary at build time.

**New workflow:**
```bash
# User edits keymap via TUI or web
roki run
# → writes roki-firmware-rs/config/default.json

# User rebuilds + flashes
cd roki-firmware-rs
cargo build --release
elf2uf2-rs ...
# → flash to both halves
```

**Future:** Web configurator could output a serialized `postcard` blob directly, and the firmware accepts it over BLE OTA or serial.

---

## 12. Testing Strategy

| Test type | Current (CP) | New (Rust) |
|---|---|---|
| Unit tests | `pytest` with mocks | `cargo test` on host (no-std with `std` feature for tests) |
| Integration | `pytest` with mocked BLE | `tokio` tests simulating channels + GATT events |
| Hardware-in-loop | Manual | `probe-rs` + `defmt` logs; HIL test harness via `serial_test` |
| Keymap diff | Python parses JSON | Rust parses same JSON → compare layer enums |

**Mocking BLE:** Extract `side/primary.rs` and `side/secondary.rs` behind a trait so unit tests can inject fake connections and channels.

---

## 13. Incremental Milestones

Rather than a big-bang rewrite, tackle in this order:

1. **M0 — Project skeleton**
   - `cargo new --bin roki-firmware-rs`
   - `memory.x`, `Cargo.toml`, `build.rs`
   - `cargo build` produces ELF; `probe-rs run` streams `defmt` logs.
   - Blinky LED task as proof of life.

2. **M1 — Matrix + Buzzer**
   - Port `matrix.rs` + `buzzer.rs`.
   - Pressing keys plays tones on buzzer (no HID).
   - Test on single half with `defmt` log output.

3. **M2 — Encoder + Thumbstick**
   - Port `encoder.rs` (QDEC) + `thumbstick.rs` (SAADC + calibration).
   - Test normalization and calibration write/read to flash.

4. **M3 — USB HID (fallback)**
   - Implement keyboard-only HOGP or USB HID via `embassy-usb`.
   - Single half types keys to a host.
   - Validate against `hidapi` or `usbhid` tools.

5. **M4 — BLE custom service (inter-half)**
   - Implement `RokiService` on both sides.
   - Secondary sends dummy packets; primary receives and logs them.
   - No HID yet — just verify BLE link.

6. **M5 — BLE HID + split keyboard**
   - Full HOGP implementation.
   - Primary scans its matrix AND processes secondary packets, dispatching unified HID.
   - Encoder and thumbstick on both sides work end-to-end.

7. **M6 — Layers + keymap**
   - Port `layers.rs` + `keymap.rs`.
   - Load `config.json` at boot.
   - Feature parity with CircuitPython firmware.

8. **M7 — Calibration polish + optimizations**
   - Boot-time calibration with buzzer feedback.
   - Power profiling, connection interval tuning.
   - Battery service support.

9. **M8 — Host tooling integration**
   - Export `config.json` from Python CLI into firmware build.
   - One-command `roki flash` that builds, converts to UF2, and copies.

---

## 14. Alternative: Use `rumcake`

If the above feels like too much boilerplate, evaluate [**rumcake**](https://github.com/Univa/rumcake) before starting M3.

Rumcake provides:
- Matrix scanning with debounce
- Layer system (tap/hold/toggle)
- USB + BLE HID
- Split keyboard support over BLE
- Keymap DSL (Rust macros, not JSON)

**Trade-offs:**
- Pro: Could cut months of work.
- Con: Less control over calibration, buzzer sequences, custom GATT services.
- Decision: Spike it for 1–2 days. If it covers 80% of needs, fork/contribute upstream for the remaining 20%.

---

## 15. Open Questions

1. **SoftDevice license:** Nordic SoftDevice is royalty-free but closed-source. Verify redistribution terms for open-source firmware.
2. **UF2 vs probe-rs:** Does the nice!nano v2 expose SWD pins? If not, UF2 is the only viable flash path.
3. **Calibrated ADC accuracy:** The SAADC on nRF52840 is 12-bit. Current CP uses 16-bit values from `AnalogIn.value`. Verify scaling.
4. **Connection interval 7.5 ms:** Is this achievable and stable? ZMK uses similar intervals but tuning may be needed.
5. **Mouse report format:** Current code sends relative X/Y in the mouse report. Does the host OS need a separate `mousemove` report ID?
6. **Bootloader persistence:** Does flashing a new app via UF2 preserve the flash page used for calibration? The Nordic bootloader shouldn't erase application flash unless the page is part of the new image.

---

## 16. References

- [nice!nano v2 pinout](https://nicekeyboards.com/docs/nice-nano/pinout-schematic/)
- [Embassy nRF HAL docs](https://docs.embassy.dev/embassy-nrf/)
- [nrf-softdevice examples](https://github.com/embassy-rs/nrf-softdevice/tree/master/examples)
- [USB HID Usage Tables (HUT1_12v2)](https://www.usb.org/sites/default/files/documents/hut1_12v2.pdf)
- [Rumcake keyboard framework](https://github.com/Univa/rumcake)
- [ZMK (Zephyr-based split keyboard fw)](https://zmk.dev/) — good reference for HOGP and split BLE architecture
