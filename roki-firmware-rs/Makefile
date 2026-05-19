.PHONY: all build release uf2 flash check clean

TARGET := thumbv7em-none-eabihf
BINARY := roki-firmware
RELEASE_DIR := target/$(TARGET)/release

all: uf2

build:
	cargo build

release:
	cargo build --release

uf2: release
	elf2uf2-rs $(RELEASE_DIR)/$(BINARY) $(BINARY).uf2
	@echo "Created $(BINARY).uf2"

check:
	cargo check

clean:
	cargo clean
	rm -f $(BINARY).uf2
