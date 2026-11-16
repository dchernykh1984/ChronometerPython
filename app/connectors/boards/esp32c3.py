"""The ESP32-C3 beam board: beam/firmware/esp32c3/main.py, MicroPython on an ESP32-C3
SuperMini, on its USB or on its own Bluetooth; beam/README.md says how to build, wire
and flash one."""

from __future__ import annotations

from app.connectors.boards import Board
from app.connectors.boards.rp2040 import FIRMWARE  # one firmware core for every chip

BOARD = Board(
    name="beam-esp32c3",
    label="Beam board ESP32-C3 (USB)",
    hello="beam-esp32c3",
    firmware=FIRMWARE,
    vendor=0x303A,  # Espressif
    product=0x1001,  # the chip's own USB Serial/JTAG
    # RTS on holds the chip in reset, and DTR on as RTS goes off starts its bootloader:
    # both off, DTR first. MicroPython there needs neither.
    lines=False,
)

RADIO = Board(
    name="beam-esp32c3-ble",
    label="Beam board ESP32-C3 (Bluetooth)",
    hello="beam-esp32c3",
    firmware=FIRMWARE,
    transport="ble",
)
