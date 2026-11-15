"""Beam boards the chronometer reads itself: one module for each.

A board's module names it and gives the USB ids of its serial port and the firmware
the chronometer reads (rp2040.py). What any board says is the beam board contract,
specs/001-event-sources/contracts/beam-board-protocol.md, read by protocol.py; and
usb_serial.py carries it over a USB serial port. A board on another chip is another
module like rp2040.py; one on Bluetooth, another transport beside usb_serial.py.
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
    vendor: int  # the USB ids of its serial port
    product: int


def boards() -> dict[str, Board]:
    """Every board the chronometer reads, by connector name."""
    from app.connectors.boards import rp2040

    return {board.name: board for board in (rp2040.BOARD,)}
