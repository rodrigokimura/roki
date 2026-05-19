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

### Flash

Double-tap the reset button on the nice!nano to enter bootloader mode, then copy the UF2:

```bash
cp roki-firmware.uf2 /media/NICENANO/
```

## Side selection

The firmware is compiled for the **right (secondary)** side by default.
To build for the **left (primary)** side:

```bash
cargo build --release --features left-side
```

## Architecture

| Module | Responsibility |
|--------|----------------|
| `main.rs` | Embassy executor init, spawns tasks, side detection |
| `matrix.rs` | 5×6 GPIO matrix scan with debounce |
| `encoder.rs` | QDEC peripheral task |
| `thumbstick.rs` | SAADC sampling + calibration normalization |
| `buzzer.rs` | PWM note sequencer |
| `keymap.rs` | HID keycodes, mouse directions, layer commands |
| `layers.rs` | Layer state machine (press/hold/inc/dec/toggle-extras) |
| `config.rs` | Compile-time JSON keymap parsing |
| `calibration.rs` | Flash-backed calibration data |
| `protocol.rs` | Inter-half BLE packet format |
| `side/primary.rs` | Left half: HID host + BLE central |
| `side/secondary.rs` | Right half: BLE peripheral + custom GATT service |
| `ble/hid_service.rs` | HOGP report map (keyboard + mouse + consumer) |
| `ble/roki_service.rs` | Custom inter-half GATT service |

## Debug logs

The firmware uses `defmt` + `defmt-rtt` for structured logging. Connect a debugger (e.g. probe-rs) and run:

```bash
cargo run --release
```

This will stream RTT logs automatically.

## Keymap

The default keymap is embedded at compile time from `config/default.json`. Edit the JSON, then rebuild:

```bash
roki run        # from repo root — edits config.json via TUI
cd roki-firmware-rs && make uf2
```

## Milestones

- [x] M0 — Project skeleton (`cargo build` passes)
- [x] M1 — Matrix scanner + Buzzer PWM tones
- [x] M2 — Encoder (QDEC) + Thumbstick (SAADC + calibration)
- [x] Keycodes — Full keypad + application keys
- [x] Build — UF2 conversion script
- [ ] M3/M4 — SoftDevice init, BLE advertising, HOGP registration
- [ ] M5 — Full split-keyboard HID end-to-end
- [ ] M6 — Boot-time calibration procedure
- [ ] M7 — Battery service + power tuning
- [ ] M8 — Host tooling (`roki flash` one-command)
