"""The RP2040 beam board: beam/firmware/rp2040/main.py, MicroPython on a Waveshare
RP2040-Zero or a clone; its README says how to build, wire and flash one."""

from __future__ import annotations

from app.connectors.boards import Board

# beam/firmware/core/beamcore.py's FIRMWARE: a test keeps the two the same.
FIRMWARE = "0.4"

BOARD = Board(
    name="beam-rp2040",
    label="Beam board RP2040 (USB)",
    hello="beam-rp2040",
    firmware=FIRMWARE,
    vendor=0x2E8A,  # Raspberry Pi: the RP2040's MicroPython port
    product=0x0005,  # MicroPython's, not a Raspberry Pi Debug Probe's
)
