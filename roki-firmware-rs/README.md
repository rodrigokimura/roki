# roki-firmware-rs

Rust + Embassy firmware for the RoKi split keyboard.

## Build

### Prerequisites

- `rustup` with `thumbv7em-none-eabihf` target:
  ```bash
  rustup target add thumbv7em-none-eabihf
  ```
- `elf2uf2-rs` for UF2 conversion:
  ```bash
  cargo install elf2uf2-rs
  ```

### Compile

```bash
cargo build --release
```

### Convert to UF2 (nice!nano bootloader)

```bash
make uf2
# or
./build-uf2.sh
```

This produces `roki-firmware.uf2`.

## Flashing (UF2 bootloader)

The nice!nano v2 uses a UF2 bootloader — no debug probe required.

| Step | Action |
|---|---|
| 1 | **Enter bootloader** — double-tap the reset button on the nice!nano. An LED flashes. A mass-storage drive named `NICENANO` appears. |
| 2 | **Copy UF2** — `cp roki-firmware.uf2 /media/NICENANO/` (Linux) or drag-and-drop in Finder (macOS). The drive unmounts automatically. |
| 3 | **Repeat for both halves** — the left half needs `--features left-side`, the right half is the default build. |

### Side selection

| Side | Build command |
|---|---|
| Right (secondary, default) | `cargo build --release` |
| Left (primary) | `cargo build --release --features left-side` |

Then convert each:
```bash
# Right half
cargo build --release
make uf2
cp roki-firmware.uf2 /media/NICENANO/

# Left half
cargo build --release --features left-side
make uf2
cp roki-firmware.uf2 /media/NICENANO/
```

## On-device testing guide

### Required hardware

- 2× nice!nano v2
- 1× debug probe (optional but recommended for logs): J-Link, CMSIS-DAP, or Raspberry Pi Debug Probe
- 1× USB-C cable per half (power + data)

### 1. Check serial output (defmt-rtt)

If you have a debug probe, connect `SWDIO/SWCLK/GND` to the nice!nano header and run:

```bash
cargo run --release --features left-side
```

RTT logs stream automatically. You should see:
```
INFO  RoKi firmware starting...
INFO  Side detected: LEFT (primary)
INFO  Loaded 2 layers from config
INFO  Playing tone sequence          ← startup buzzer
INFO  Found secondary at address ...
INFO  Connected to secondary ...
INFO  HID reports active — keyboard + mouse + consumer
```

### 2. Test matrix (defmt logging)

Press any key on the **right half** while monitoring the log:
```
TRACE TX KEY packet: [0x05, 0x01, 0x02, 0x01]    ← secondary→primary
TRACE RX inter-half packet: [0x05, 0x01, 0x02, 0x01]  ← primary received it
```

Press any key on the **left half** — no inter-half packet is sent, but the HID report should show in a host-side HID inspector app.

### 3. Test HID host connectivity

| Check | How |
|---|---|
| Bluetooth Low Energy visible | On a phone or laptop, scan for BLE devices. You should see `"Roki"` with service `0x1812` (HID). |
| Pair & connect | Click connect. The primary half should beep a high-pitch ascending triad (`queue_host_connected_tone`). |
| Keyboard typing | Open any text input. Press keys on both halves. Both should type. |
| Mouse movement | On a non-Apple host (Linux/Windows), move the thumbstick — the cursor should move. |
| Consumer/media keys | If your keymap has `PLAY_PAUSE`, `VOLUME_INCREMENT`, etc., test them in a media player. |

### 4. Test hardware tasks in isolation

These logs are emitted continuously at `DEBUG`/`TRACE` level. Increase log verbosity:

```bash
DEFMT_LOG=trace cargo run --release --features left-side
```

| Task | Expected log |
|---|---|
| `matrix_task` | `TRACE Key event idx=12 pressed=true` |
| `encoder_task` | `TRACE Encoder delta=-2` |
| `thumbstick_task` | `TRACE Thumbstick raw=(1452, 1987) norm=(0.2, -0.1)` |
| `buzzer_task` | `INFO Playing tone sequence` |
| `secondary_link_task` | `INFO Found secondary at address …` / `INFO Connected to secondary …` |
| `host_link_task` | `INFO Host connected: …` |

### 5. Boot-time calibration

Hold the thumbstick switch while powering on (or resetting) the **primary half**. The buzzer plays a startup tone and the log shows:

```
INFO  Thumbstick switch held at boot — entering calibration mode
INFO  Release thumbstick switch to begin center sampling...
INFO  Sampling center — hold thumbstick neutral for 5 s...
INFO  Center sampled: x=1452 y=1987
INFO  Rotate thumbstick to all edges, then press switch to finish...
INFO  Extents sampled: x=[1023, 1890] y=[1670, 2340]
```

The calibration is written to flash and survives reboots.

### 6. Reconnection resilience

| Test | Expected behavior |
|---|---|
| Turn off the right half | Primary log: `WARN Secondary disconnected — reconnecting in 1s...`. Typing on left half continues to work via HID. Power right half back on — auto-reconnects, buzzer chime plays. |
| Disable Bluetooth on host | Primary: `WARN Host slot refresh — clearing stale connection`. Re-enable Bluetooth — `"Roki"` reappears, connect again. |

### 7. Power consumption (optional)

Measure current draw with a multimeter in series with the battery connector:
- Idle (connected, no keys pressed): ~1.5–2.5 mA
- Active typing: ~3–5 mA
- Advertising without host: ~5–8 mA

### Debug probe pinout (nice!nano v2)

```
Debug Header (SWD)
┌────────────┐
│ VTref 3.3V │  ← optional power sense
│ SWDIO      │  ← data
│ SWCLK      │  ← clock
│ GND        │  ← ground
└────────────┘
```

Connect to your probe and run:
```bash
probe-rs run --chip nRF52840_xxAA target/thumbv7em-none-eabihf/release/roki-firmware
```

### Quick reference: one-liners

```bash
# Right half (UF2)
cargo build --release && make uf2

# Left half (UF2)
cargo build --release --features left-side && make uf2

# Left half with live RTT logs
cargo run --release --features left-side

# Left half with trace logs
cargo run --release --features left-side -- DEFMT_LOG=trace

# Clean
cargo clean && rm -f *.uf2
```

### 8. Change the keymap (compile-time)

The keymap JSON (`config/default.json`) is embedded at build time via `include_str!`. Edit it, then rebuild both halves:

```bash
# Edit roki-firmware-rs/config/default.json
# Then rebuild:
cd roki-firmware-rs

# Right half
cargo build --release && make uf2

# Left half
cargo build --release --features left-side && make uf2
```

There is **no runtime filesystem** on the nice!nano, so every keymap change currently requires recompilation. A future milestone (M9) will add USB MSC drag-and-drop support for live keymap updates without rebuilding.

## Future milestones

- [ ] M7 — Battery service + power tuning
- [ ] M8 — Host tooling (`roki flash` one-command)
- [ ] M9 — **USB Mass Storage Class (MSC) drag-and-drop keymap**

### M9 — USB Mass Storage keymap (planned)

The CircuitPython firmware exposed the nice!nano as a USB storage device when plugged into a PC, allowing users to drag-and-drop a `config.json` to change the keymap without recompiling. The Rust port will replicate this with `embassy-usb`:

| Aspect | Plan |
|---|---|
| USB class | MSC (Mass Storage Class) over `embassy-usb` |
| Filesystem | Tiny virtual FAT12/16 image in flash or RAM |
| Exposed file | `config.json` (read/write) |
| Detection | Monitor SCSI `WRITE(10)` to detect file modification |
| Validation | Parse incoming JSON with `serde-json-core`, validate key names |
| Reload | Store validated config to a dedicated flash page; load at next boot |
| Safety | Keep a CRC-32 checksum; fallback to embedded default on parse failure |
| Coexistence | MSC only activates when USB VBUS is detected and no BLE host is connected (avoid HID/MSC composite complexity) |

This avoids the recompilation step for non-technical users and matches the Python firmware's workflow exactly.

## Architecture
|--------|----------------|
| `main.rs` | Embassy executor init, task spawning, side detection |
| `matrix.rs` | 5×6 GPIO matrix scan |
| `encoder.rs` | QDEC peripheral task |
| `thumbstick.rs` | SAADC sampling + boot-time calibration + normalization |
| `buzzer.rs` | PWM note sequencer |
| `keymap.rs` | HID keycodes, mouse directions, media codes, layer commands |
| `layers.rs` | Layer state machine (press/hold/inc/dec/toggle-extras) |
| `config.rs` | Compile-time JSON keymap parsing via `serde-json-core` |
| `calibration.rs` | Flash-backed `CalibrationData` read/write via NVMC |
| `protocol.rs` | 4-byte inter-half packet format (backward-compatible with Python) |
| `side/primary.rs` | Left half: HID host (HOGP), BLE central (secondary link), auto-reconnect loops |
| `side/secondary.rs` | Right half: BLE peripheral (custom GATT), input→packet notify, auto-reconnect loop |
| `ble/hid_service.rs` | HOGP report map (keyboard + mouse + consumer + media) |
| `ble/roki_service.rs` | Custom inter-half GATT service (`RokiServer` + `RokiClient`) |
| `ble/mod.rs` | SoftDevice init for nice!nano v2 (RC clock, 2 connections) |

## Milestones

- [x] M0 — Project skeleton (`cargo build` passes)
- [x] M1 — Matrix, encoder, thumbstick, buzzer hardware tasks
- [x] M2 — Keymap parsing, layers, config JSON embedding
- [x] Keycodes — full keypad + application + media keys
- [x] Build — UF2 conversion (`make uf2`)
- [x] M3/M4 — SoftDevice init, BLE advertising, custom GATT service, scan/connect, inter-half packets
- [x] M5 — HID over GATT (HOGP): report map, input reports, host advertising, keyboard/mouse/consumer dispatch
- [x] Boot calibration — switch-hold at boot, 5s center sample, edge rotation, flash save
- [x] Reconnection — auto-retry loops for host and secondary on both halves
- [ ] M7 — Battery service + power tuning
- [ ] M8 — Host tooling (`roki flash` one-command)
- [ ] M9 — **USB Mass Storage Class (MSC) drag-and-drop keymap**
