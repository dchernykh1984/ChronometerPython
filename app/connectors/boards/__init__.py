"""Beam boards the chronometer reads itself: one module for each.

A board's module names it, on each of its links, and gives the USB ids of its serial
port and the firmware the chronometer reads (rp2040.py, esp32c3.py). What any board
says is the beam board contract,
specs/001-event-sources/contracts/beam-board-protocol.md, read by protocol.py;
usb_serial.py carries it over a USB serial port, ble.py over Bluetooth. A board on
another chip is another module like rp2040.py.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Board:
    """A beam board as the chronometer knows it."""

    name: str  # the connector's name, as the device list keeps it
    label: str  # as the device list shows it
    hello: str  # the name its HELLO gives
    firmware: str  # the version its HELLO is to give
    vendor: int | None = None  # the USB ids of its serial port
    product: int | None = None
    transport: str = "usb"  # "usb" or "ble"


def boards() -> dict[str, Board]:
    """Every board the chronometer reads, by connector name."""
    from app.connectors.boards import esp32c3, rp2040

    every = (rp2040.BOARD, rp2040.RADIO, esp32c3.BOARD, esp32c3.RADIO)
    return {board.name: board for board in every}
