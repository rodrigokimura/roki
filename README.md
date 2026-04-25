# RoKi

> An ergonomic, wireless, split mechanical keyboard — hardware, firmware and tooling in one repo.

**RoKi** (from the author's surname) is a custom, from-scratch split keyboard project. It covers the full stack: PCB design, 3D-printable case parts, CircuitPython firmware running on the [nice!nano v2](https://nicekeyboards.com/docs/nice-nano/) (wireless Bluetooth Low Energy controller), and a companion Python CLI / web UI / TUI to flash, configure and debug the board.

> ⚠️ **Status:** Work in progress. Breaking changes are expected.

---

## Features

- **Split layout** with BLE-based inter-half communication (no TRRS cable).
- **5 rows × 6 columns** per half, diode matrix.
- **Thumb cluster with analog thumbstick** (for pointer / scroll / layer control).
- **Rotary encoder** on each half.
- **Piezo buzzer** for audio feedback.
- **Layer system** with custom `layer_handler` (tap / hold / toggle commands).
- **HID support** for keyboard, mouse and consumer-control (media) keys, via `adafruit_hid`.
- **Per-side configuration** (primary / secondary) selected via environment.
- **Runtime calibration** of the analog thumbstick (deadzone, center, range).
- **Read-only filesystem toggle** at boot, driven by a hardware switch, so you can
  hot-swap between "keyboard mode" and "developer mode" without rebuilding firmware.

---

## Repository layout

```
roki/
├── roki/                    # Python package
│   ├── firmware/            # CircuitPython firmware (runs on nice!nano v2)
│   │   ├── boot.py          # Early boot: filesystem readonly switch
│   │   ├── code.py          # Main entry point, pin mapping
│   │   ├── kb.py            # Primary / Secondary keyboard classes
│   │   ├── keys.py          # HID key definitions and handlers
│   │   ├── layer_handler.py # Layer / Command system
│   │   ├── calibration.py   # Thumbstick calibration
│   │   ├── config.py        # Runtime config model + JSON loader
│   │   ├── service.py       # BLE service for half-to-half comms
│   │   ├── buzzer.py        # Audio feedback
│   │   ├── logging.py       # Color-coded adafruit_logging formatter
│   │   ├── params.py        # Env-based parameter singleton
│   │   └── config.json      # Default key map / layers
│   ├── cli/                 # Host-side CLI (typer)
│   │   ├── app.py           # `roki` command entry point
│   │   ├── utils.py         # Mount / unmount / lib install helpers
│   │   ├── file_management.py
│   │   ├── html_generator.py
│   │   └── logging.py
│   ├── tui/                 # Textual-based TUI key-map configurator
│   │   ├── app.py
│   │   ├── screens/
│   │   └── widgets/
│   └── templates/           # HTML templates for the web UI
├── tests/                   # pytest suite (firmware + cli)
├── kicad/roki/              # PCB design (schematic, layout, 3D step)
├── freecad/                 # Case, keycaps, thumbstick, encoder, etc.
├── conftest.py              # Global mocks for CircuitPython modules
└── pyproject.toml
```

---

## Hardware

| Item                | Choice                                        |
|---------------------|-----------------------------------------------|
| Microcontroller     | [nice!nano v2](https://nicekeyboards.com/docs/nice-nano/pinout-schematic/) (nRF52840, BLE) |
| Layout              | Split, 5×6 + thumb cluster + encoder per half |
| Switches            | MX-compatible, hotswap                        |
| Inter-half comms    | Bluetooth Low Energy (custom GATT service)    |
| Power               | Li-Po, per-half power switch                  |
| Analog input        | Thumbstick (X / Y + push)                     |

PCB sources live in [`kicad/roki/`](./kicad/roki/). Case, keycaps and mechanical parts live in [`freecad/`](./freecad/) as `.FCStd` files.

---

## Firmware (CircuitPython)

Runs on CircuitPython for nRF52840. The firmware is structured around a `Primary` / `Secondary` pair of keyboard halves:

- **Primary** holds the full config, scans its own matrix, talks HID over BLE to the host, and receives key events from the secondary over a custom BLE service.
- **Secondary** scans its matrix and forwards events to the primary.

The side is chosen at boot via the `IS_LEFT_SIDE` environment variable (or the `boot.py` switch pin), so the same code runs on both halves.

### Pin mapping

Defined in [`roki/firmware/code.py`](./roki/firmware/code.py):

```python
Roki(
    row_pins=("P0_24", "P1_00", "P0_11", "P1_04", "P1_06"),
    column_pins=("P0_09", "P0_10", "P1_11", "P1_13", "P1_15", "P0_02"),
    buzzer_pin="P0_06",
    thumb_stick_pins=("P0_22", "AIN7", "AIN5"),  # switch, X, Y
    encoder_pins=("P0_17", "P0_20"),
)
```

See the [nice!nano pinout & schematic](https://nicekeyboards.com/docs/nice-nano/pinout-schematic/) for reference.

### Boot-time write protection

`boot.py` reads pin `P0_22` on startup. When the switch is **open** the filesystem is mounted read-only (normal keyboard mode); when **closed**, read-write — useful for editing files over USB without your OS fighting CircuitPython.

---

## Host-side tooling

A `typer` CLI is installed as `roki`:

```sh
roki upload        # (alias: u)  Flash firmware + libs to the connected board
roki run           #             Launch the TUI key-map configurator
roki serve         #             Start the FastAPI + Jinja web config UI
roki generate      # (alias: g)  Generate static HTML / artifacts
roki config        #             Show / edit config.json
```

### Install

```sh
uv sync
```

(Uses [uv](https://docs.astral.sh/uv/) as the package manager; Python 3.12+.)

### Run the tests

```sh
uv run pytest
```

With coverage:

```sh
uv run pytest --cov=roki --cov-report=term
```

Current coverage: **88%** across ~2.3k lines of source with 109 tests.

### Run the web configurator locally (HTTPS)

```sh
# Generate self-signed certs once
openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365

uv run roki serve
```

---

## Environment variables

Set in `roki/firmware/settings.toml` on the board, or via your shell for host-side runs:

| Variable        | Default | Meaning                                     |
|-----------------|---------|---------------------------------------------|
| `IS_LEFT_SIDE`  | `1`     | `1` for primary (left), `0` for secondary   |
| `DEBUG`         | `0`     | `1` enables the stream logger               |
| `LOG_LEVEL`     | `0`     | Standard logging levels (10 = DEBUG, etc.)  |

---

## Development workflow

This repo uses [commitizen](https://commitizen-tools.github.io/commitizen/) for [Conventional Commits](https://www.conventionalcommits.org/) and [ruff](https://docs.astral.sh/ruff/) for linting / import sorting.

```sh
uv run cz commit            # interactive commit
uv run ruff check --fix .   # lint + autofix
uv run ruff format .        # format
```

Pre-commit hooks are configured in [`.pre-commit-config.yaml`](./.pre-commit-config.yaml).

---

## License

[MIT](./LICENSE) © Rodrigo Eiti Kimura
