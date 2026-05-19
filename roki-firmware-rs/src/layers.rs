/// Layer state machine.
///
/// Ported from `roki/firmware/layer_handler.py`.

use crate::logging::debug;

/// A command that mutates the layer state.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum LayerCommand {
    /// No operation.
    Noop,
    /// Press a layer index (switch to it, does not restore on release).
    Press(usize),
    /// Hold a layer index (switch to it, restore previous on release).
    Hold(usize),
    /// Increment layer index (clamp to max).
    Increment,
    /// Decrement layer index (clamp to 0).
    Decrement,
    /// Toggle "extras" flag (encoder + thumbstick enable).
    ToggleExtras,
}

/// Manages active layer index and the `extras` flag.
pub struct LayerHandler<const N: usize> {
    current: usize,
    previous: usize,
    pub extras: bool,
    max_layer: usize,
}

impl<const N: usize> LayerHandler<N> {
    pub const fn new() -> Self {
        Self {
            current: 0,
            previous: 0,
            extras: false,
            max_layer: N - 1,
        }
    }

    pub fn current(&self) -> usize {
        self.current
    }

    pub fn on_press(&mut self, cmd: LayerCommand) -> bool {
        match cmd {
            LayerCommand::Noop => false,
            LayerCommand::Press(idx) => {
                if idx != self.current {
                    self.previous = self.current;
                    self.current = idx;
                    true // layer changed: caller should release_all
                } else {
                    false
                }
            }
            LayerCommand::Hold(idx) => {
                self.previous = self.current;
                self.current = idx;
                true
            }
            LayerCommand::Increment => {
                if self.current < self.max_layer {
                    self.previous = self.current;
                    self.current += 1;
                    true
                } else {
                    false
                }
            }
            LayerCommand::Decrement => {
                if self.current > 0 {
                    self.previous = self.current;
                    self.current -= 1;
                    true
                } else {
                    false
                }
            }
            LayerCommand::ToggleExtras => {
                self.extras = !self.extras;
                debug!("Extras toggled: {}", self.extras);
                false
            }
        }
    }

    pub fn on_release(&mut self, cmd: LayerCommand) -> bool {
        match cmd {
            LayerCommand::Hold(_) => {
                self.current = self.previous;
                true // layer changed: caller should release_all
            }
            _ => false,
        }
    }
}
