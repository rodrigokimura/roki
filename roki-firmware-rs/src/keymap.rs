/// Key action definitions and HID report construction.
///
/// This module translates the "key names" from `config.json` into
/// concrete HID keycodes, mouse buttons, media codes, and layer
/// commands. It also owns the global HID report state that the
/// primary side sends to the host.

use heapless::Vec;
use serde::{Deserialize, Serialize};

use crate::layers::LayerCommand;
use crate::logging::debug;

// ── HID keycodes (USB HID Usage Tables) ───────────────────────────────
// Only the subset used by the current keymap is defined; extend as needed.

/// USB HID Usage Page: Generic Desktop (0x01)
pub mod usage_page {
    pub const GENERIC_DESKTOP: u16 = 0x01;
    pub const KEYBOARD: u16 = 0x07;
    pub const CONSUMER: u16 = 0x0C;
}

/// USB HID keycodes for the Keyboard usage page (0x07).
#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[repr(u8)]
pub enum Keycode {
    None = 0x00,
    A = 0x04,
    B = 0x05,
    C = 0x06,
    D = 0x07,
    E = 0x08,
    F = 0x09,
    G = 0x0A,
    H = 0x0B,
    I = 0x0C,
    J = 0x0D,
    K = 0x0E,
    L = 0x0F,
    M = 0x10,
    N = 0x11,
    O = 0x12,
    P = 0x13,
    Q = 0x14,
    R = 0x15,
    S = 0x16,
    T = 0x17,
    U = 0x18,
    V = 0x19,
    W = 0x1A,
    X = 0x1B,
    Y = 0x1C,
    Z = 0x1D,
    One = 0x1E,
    Two = 0x1F,
    Three = 0x20,
    Four = 0x21,
    Five = 0x22,
    Six = 0x23,
    Seven = 0x24,
    Eight = 0x25,
    Nine = 0x26,
    Zero = 0x27,
    Enter = 0x28,
    Escape = 0x29,
    Backspace = 0x2A,
    Tab = 0x2B,
    Spacebar = 0x2C,
    Minus = 0x2D,
    Equals = 0x2E,
    LeftBracket = 0x2F,
    RightBracket = 0x30,
    Backslash = 0x31,
    Semicolon = 0x33,
    Quote = 0x34,
    GraveAccent = 0x35,
    Comma = 0x36,
    Period = 0x37,
    ForwardSlash = 0x38,
    CapsLock = 0x39,
    F1 = 0x3A,
    F2 = 0x3B,
    F3 = 0x3C,
    F4 = 0x3D,
    F5 = 0x3E,
    F6 = 0x3F,
    F7 = 0x40,
    F8 = 0x41,
    F9 = 0x42,
    F10 = 0x43,
    F11 = 0x44,
    F12 = 0x45,
    PrintScreen = 0x46,
    ScrollLock = 0x47,
    Pause = 0x48,
    Insert = 0x49,
    Home = 0x4A,
    PageUp = 0x4B,
    Delete = 0x4C,
    End = 0x4D,
    PageDown = 0x4E,
    RightArrow = 0x4F,
    LeftArrow = 0x50,
    DownArrow = 0x51,
    UpArrow = 0x52,
    LeftControl = 0xE0,
    LeftShift = 0xE1,
    LeftAlt = 0xE2,
    LeftGui = 0xE3,
    RightControl = 0xE4,
    RightShift = 0xE5,
    RightAlt = 0xE6,
    KeypadNumlock = 0x53,
    KeypadSlash = 0x54,
    KeypadAsterisk = 0x55,
    KeypadMinus = 0x56,
    KeypadPlus = 0x57,
    KeypadEnter = 0x58,
    KeypadOne = 0x59,
    KeypadTwo = 0x5A,
    KeypadThree = 0x5B,
    KeypadFour = 0x5C,
    KeypadFive = 0x5D,
    KeypadSix = 0x5E,
    KeypadSeven = 0x5F,
    KeypadEight = 0x60,
    KeypadNine = 0x61,
    KeypadZero = 0x62,
    KeypadPeriod = 0x63,
    Application = 0x65,
    RightGui = 0xE7,
}

impl Keycode {
    pub fn modifier_bit(&self) -> Option<u8> {
        let v = *self as u8;
        if (0xE0..=0xE7).contains(&v) {
            Some(1 << (v - 0xE0))
        } else {
            None
        }
    }
}

/// Consumer/media control codes (Usage Page 0x0C).
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(u16)]
pub enum ConsumerCode {
    PlayPause = 0xCD,
    Stop = 0xB7,
    VolumeIncrement = 0xE9,
    VolumeDecrement = 0xEA,
    Mute = 0xE2,
    ScanNextTrack = 0xB5,
    ScanPreviousTrack = 0xB6,
}

// ── KeyAction ─────────────────────────────────────────────────────────

/// A single key cell in the keymap.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum KeyAction {
    /// Do nothing.
    Noop,
    /// Standard HID keyboard keycode.
    Keyboard(Keycode),
    /// Mouse button press (bits 0..2 = left, right, middle).
    MouseButton(u8),
    /// Mouse directional movement (reported as relative X/Y or wheel).
    MouseMove(MouseDirection),
    /// HID consumer/media control code.
    Media(ConsumerCode),
    /// Layer switch command.
    Layer(LayerCommand),
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum MouseDirection {
    Up,
    Down,
    Left,
    Right,
    ScrollUp,
    ScrollDown,
}

// ── Parsing strings from config.json ────────────────────────

impl KeyAction {
    /// Parse a key name string from the JSON config into a `KeyAction`.
    ///
    /// This is the Rust equivalent of `BaseKey.build()` in the Python firmware.
    pub fn from_str(s: &str) -> Self {
        use Keycode::*;
        use MouseDirection::*;

        // Layer commands first
        if s.eq_ignore_ascii_case("LAYER_EXTRAS") {
            return KeyAction::Layer(LayerCommand::ToggleExtras);
        }
        if s.len() > 6 && s[..6].eq_ignore_ascii_case("LAYER_") {
            let rest = &s[6..];
            if let Some((idx_str, cmd)) = rest.rsplit_once('_') {
                if let Ok(idx) = idx_str.parse::<usize>() {
                    let action = match cmd {
                        "PRESS" => LayerCommand::Press(idx),
                        "HOLD" => LayerCommand::Hold(idx),
                        "INC" => LayerCommand::Increment,
                        "DEC" => LayerCommand::Decrement,
                        "EXTRAS" => LayerCommand::ToggleExtras,
                        _ => LayerCommand::Noop,
                    };
                    return KeyAction::Layer(action);
                }
            }
        }

        // Mouse movement
        match s {
            "MOUSE_MOVE_UP" => return KeyAction::MouseMove(Up),
            "MOUSE_MOVE_DOWN" => return KeyAction::MouseMove(Down),
            "MOUSE_MOVE_LEFT" => return KeyAction::MouseMove(Left),
            "MOUSE_MOVE_RIGHT" => return KeyAction::MouseMove(Right),
            "MOUSE_SCROLL_UP" => return KeyAction::MouseMove(ScrollUp),
            "MOUSE_SCROLL_DOWN" => return KeyAction::MouseMove(ScrollDown),
            _ => {}
        }

        // Keyboard keycodes
        let kc = match s {
            "A" => A,
            "B" => B,
            "C" => C,
            "D" => D,
            "E" => E,
            "F" => F,
            "G" => G,
            "H" => H,
            "I" => I,
            "J" => J,
            "K" => K,
            "L" => L,
            "M" => M,
            "N" => N,
            "O" => O,
            "P" => P,
            "Q" => Q,
            "R" => R,
            "S" => S,
            "T" => T,
            "U" => U,
            "V" => V,
            "W" => W,
            "X" => X,
            "Y" => Y,
            "Z" => Z,
            "ONE" => One,
            "TWO" => Two,
            "THREE" => Three,
            "FOUR" => Four,
            "FIVE" => Five,
            "SIX" => Six,
            "SEVEN" => Seven,
            "EIGHT" => Eight,
            "NINE" => Nine,
            "ZERO" => Zero,
            "ENTER" => Enter,
            "ESCAPE" => Escape,
            "BACKSPACE" => Backspace,
            "TAB" => Tab,
            "SPACEBAR" => Spacebar,
            "MINUS" => Minus,
            "EQUALS" => Equals,
            "LEFT_BRACKET" => LeftBracket,
            "RIGHT_BRACKET" => RightBracket,
            "BACKSLASH" => Backslash,
            "KEYPAD_BACKSLASH" => Backslash,
            "SEMICOLON" => Semicolon,
            "QUOTE" => Quote,
            "GRAVE_ACCENT" => GraveAccent,
            "COMMA" => Comma,
            "PERIOD" => Period,
            "FORWARD_SLASH" => ForwardSlash,
            "CAPS_LOCK" => CapsLock,
            "F1" => F1,
            "F2" => F2,
            "F3" => F3,
            "F4" => F4,
            "F5" => F5,
            "F6" => F6,
            "F7" => F7,
            "F8" => F8,
            "F9" => F9,
            "F10" => F10,
            "F11" => F11,
            "F12" => F12,
            "PRINT_SCREEN" => PrintScreen,
            "SCROLL_LOCK" => ScrollLock,
            "PAUSE" => Pause,
            "INSERT" => Insert,
            "HOME" => Home,
            "PAGE_UP" => PageUp,
            "DELETE" => Delete,
            "END" => End,
            "PAGE_DOWN" => PageDown,
            "RIGHT_ARROW" => RightArrow,
            "LEFT_ARROW" => LeftArrow,
            "DOWN_ARROW" => DownArrow,
            "UP_ARROW" => UpArrow,
            "LEFT_CONTROL" => LeftControl,
            "LEFT_SHIFT" => LeftShift,
            "LEFT_ALT" => LeftAlt,
            "LEFT_GUI" => LeftGui,
            "RIGHT_CONTROL" => RightControl,
            "RIGHT_SHIFT" => RightShift,
            "RIGHT_ALT" => RightAlt,
            "RIGHT_GUI" => RightGui,
            "KEYPAD_NUMLOCK" => KeypadNumlock,
            "KEYPAD_SLASH" => KeypadSlash,
            "KEYPAD_ASTERISK" => KeypadAsterisk,
            "KEYPAD_MINUS" => KeypadMinus,
            "KEYPAD_PLUS" => KeypadPlus,
            "KEYPAD_ENTER" => KeypadEnter,
            "KEYPAD_1" => KeypadOne,
            "KEYPAD_2" => KeypadTwo,
            "KEYPAD_3" => KeypadThree,
            "KEYPAD_4" => KeypadFour,
            "KEYPAD_5" => KeypadFive,
            "KEYPAD_6" => KeypadSix,
            "KEYPAD_7" => KeypadSeven,
            "KEYPAD_8" => KeypadEight,
            "KEYPAD_9" => KeypadNine,
            "KEYPAD_0" => KeypadZero,
            "KEYPAD_PERIOD" => KeypadPeriod,
            "APPLICATION" => Application,
            "PLAY_PAUSE" => return KeyAction::Media(ConsumerCode::PlayPause),
            "VOLUME_INCREMENT" => return KeyAction::Media(ConsumerCode::VolumeIncrement),
            "VOLUME_DECREMENT" => return KeyAction::Media(ConsumerCode::VolumeDecrement),
            "MUTE" => return KeyAction::Media(ConsumerCode::Mute),
            "SCAN_NEXT_TRACK" => return KeyAction::Media(ConsumerCode::ScanNextTrack),
            "SCAN_PREVIOUS_TRACK" => return KeyAction::Media(ConsumerCode::ScanPreviousTrack),
            _ => {
                debug!("Unknown key string: {}", s);
                return KeyAction::Noop;
            }
        };
        KeyAction::Keyboard(kc)
    }
}

// ── HID Report builders ──────────────────────────────────────────────

/// Standard 8-byte boot keyboard report.
#[derive(Clone, Copy, Debug, Default)]
pub struct KeyboardReport {
    pub modifiers: u8,
    pub reserved: u8,
    pub keys: [u8; 6],
}

/// Mouse report: buttons, X, Y, wheel.
#[derive(Clone, Copy, Debug, Default)]
pub struct MouseReport {
    pub buttons: u8,
    pub x: i8,
    pub y: i8,
    pub wheel: i8,
}

/// Consumer report: up to 4 media keys (bit-packed).
#[derive(Clone, Copy, Debug, Default)]
pub struct ConsumerReport {
    pub usage: u16,
}

/// Aggregated HID state that the primary side maintains.
pub struct HidState {
    pub keyboard: KeyboardReport,
    pub mouse: MouseReport,
    pub consumer: ConsumerReport,
    /// Which key slots in `keyboard.keys` are occupied by each keycode
    /// so we can release the right slot when a key lifts.
    pub active_keys: Vec<u8, 6>,
}

impl HidState {
    pub fn new() -> Self {
        Self {
            keyboard: KeyboardReport::default(),
            mouse: MouseReport::default(),
            consumer: ConsumerReport::default(),
            active_keys: Vec::new(),
        }
    }

    pub const fn new_const() -> Self {
        Self {
            keyboard: KeyboardReport {
                modifiers: 0,
                reserved: 0,
                keys: [0; 6],
            },
            mouse: MouseReport {
                buttons: 0,
                x: 0,
                y: 0,
                wheel: 0,
            },
            consumer: ConsumerReport {
                usage: 0,
            },
            active_keys: Vec::new(),
        }
    }

    pub fn press(&mut self, action: KeyAction) {
        match action {
            KeyAction::Noop => {}
            KeyAction::Keyboard(kc) => {
                let code = kc as u8;
                if let Some(bit) = kc.modifier_bit() {
                    self.keyboard.modifiers |= bit;
                } else {
                    // Find first free slot
                    for slot in &mut self.keyboard.keys {
                        if *slot == 0 {
                            *slot = code;
                            let _ = self.active_keys.push(code);
                            break;
                        }
                    }
                }
            }
            KeyAction::MouseButton(btn) => {
                self.mouse.buttons |= btn & 0x07;
            }
            KeyAction::MouseMove(dir) => {
                const SPEED: i8 = 20;
                match dir {
                    MouseDirection::Up => self.mouse.y = -SPEED,
                    MouseDirection::Down => self.mouse.y = SPEED,
                    MouseDirection::Left => self.mouse.x = -SPEED,
                    MouseDirection::Right => self.mouse.x = SPEED,
                    MouseDirection::ScrollUp => self.mouse.wheel = 2,
                    MouseDirection::ScrollDown => self.mouse.wheel = -2,
                }
            }
            KeyAction::Media(code) => {
                self.consumer.usage = code as u16;
            }
            KeyAction::Layer(_) => {
                // Layer commands are handled by the LayerHandler, not HID state
            }
        }
    }

    pub fn release(&mut self, action: KeyAction) {
        match action {
            KeyAction::Noop => {}
            KeyAction::Keyboard(kc) => {
                let code = kc as u8;
                if kc.modifier_bit().is_some() {
                    self.keyboard.modifiers &= !(kc.modifier_bit().unwrap());
                } else {
                    // Remove from active keys and zero the slot
                    self.active_keys.retain(|&k| k != code);
                    for slot in &mut self.keyboard.keys {
                        if *slot == code {
                            *slot = 0;
                        }
                    }
                }
            }
            KeyAction::MouseButton(btn) => {
                self.mouse.buttons &= !(btn & 0x07);
            }
            KeyAction::MouseMove(_) => {
                self.mouse.x = 0;
                self.mouse.y = 0;
                self.mouse.wheel = 0;
            }
            KeyAction::Media(_) => {
                self.consumer.usage = 0;
            }
            KeyAction::Layer(_) => {}
        }
    }

    /// Return the current 6-key + modifier state as (keys, modifiers).
    pub fn keyboard_report(&self) -> ([u8; 6], u8) {
        (self.keyboard.keys, self.keyboard.modifiers)
    }
    pub fn release_all(&mut self) {
        self.keyboard = KeyboardReport::default();
        self.mouse = MouseReport::default();
        self.consumer = ConsumerReport::default();
        self.active_keys.clear();
    }
}

// ── Inter-task event types ────────────────────────────────────────────

/// A single key matrix event.
#[derive(Clone, Copy, Debug)]
pub struct KeyEvent {
    pub index: u8,   // Flat index: row * COLS + col
    pub pressed: bool,
}

/// Rotary encoder event.
#[derive(Clone, Copy, Debug)]
pub struct EncoderEvent {
    pub delta: i8,   // Positive = clockwise, negative = counter-clockwise
}

/// Thumbstick normalized event.
#[derive(Clone, Copy, Debug)]
pub struct ThumbstickEvent {
    pub x: f32,   // [-1.0, 1.0]
    pub y: f32,   // [-1.0, 1.0]
    pub pressed: bool, // Switch state
}
