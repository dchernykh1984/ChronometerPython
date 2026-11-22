"""``beam-scan``: the beam boards around, on USB and on Bluetooth (spec 003, FR-001).

The chronometer starts ``<chronometer> --connector beam-scan``; this says hello, looks
for the boards (the USB ports with the boards' ids, and SCAN_S of Bluetooth for those
advertised as ``beam-`` or offering the serial service), says them in one message and
ends:

    {"type": "found", "boards": [
        {"link": "usb", "name": "beam-rp2040", "port": "COM7", "kind": "beam-rp2040"},
        {"link": "ble", "name": "beam-7c1c", "device": "<address>", "rssi": -61}]}

The USB ones first, then the nearest on Bluetooth; each as ``beam-boards`` takes it in
its pick. A link that cannot be looked on is said first, as an error. bleak runs here,
in the connector's process, never in the window's (CLAUDE.md).
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import threading
from typing import IO, Any

from app import connector_protocol as cp
from app.connectors.boards import ble, many
from app.connectors.boards.usb_serial import watch_parent

NAME = "beam-scan"


def on_usb(ports: list[Any]) -> list[dict[str, Any]]:
    """The boards on USB, of the kinds the ports' ids give."""
    kinds = {(spec.vendor, spec.product): spec for spec in many.USB_KINDS.values()}
    found = []
    for port in sorted(ports, key=lambda one: one.device):
        if (spec := kinds.get((port.vid, port.pid))) is not None:
            found.append(
                {
                    "link": "usb",
                    "name": spec.hello,
                    "port": port.device,
                    "kind": spec.hello,
                }
            )
    return found


async def on_radio(bleak: Any) -> list[dict[str, Any]]:
    """The boards on Bluetooth, the nearest first."""
    seen = await bleak.BleakScanner.discover(timeout=ble.SCAN_S, return_adv=True)
    found = [
        {
            "link": "ble",
            "name": advert.local_name or device.name or device.address,
            "device": device.address,
            "rssi": advert.rssi,
        }
        for device, advert in seen.values()
        if ble.is_board(device, advert)
    ]
    return sorted(found, key=lambda one: -one["rssi"])


def scan(stdout: IO[str], list_ports: Any, bleak: Any) -> int:
    def send(message: dict[str, Any]) -> None:
        stdout.write(json.dumps(message) + "\n")
        stdout.flush()

    send({"type": "hello", "protocol": cp.PROTOCOL, "connector": NAME, "kind": "beam"})
    boards = []
    try:
        boards += on_usb(list_ports.comports())
    except Exception as error:  # the ports cannot be listed: Bluetooth still can
        send({"type": "error", "message": f"USB: {ble.described(error)}"})
    try:
        boards += asyncio.run(on_radio(bleak))
    except Exception as error:  # Bluetooth off, or not allowed to this program
        send({"type": "error", "message": f"Bluetooth: {ble.described(error)}"})
    send({"type": "found", "boards": boards})
    return 0


def found_in(output: bytes) -> tuple[list[dict[str, Any]], list[str]]:
    """What a scan's output says: the boards found, and its errors."""
    boards: list[dict[str, Any]] = []
    errors = []
    for line in output.splitlines():
        try:
            message = json.loads(line)
        except ValueError:
            continue
        if not isinstance(message, dict):
            continue
        if message.get("type") == "error":
            errors.append(str(message.get("message")))
        elif message.get("type") == "found" and isinstance(message.get("boards"), list):
            boards = [one for one in message["boards"] if isinstance(one, dict)]
    return boards, errors


def listed(
    found: list[dict[str, Any]], picked: list[dict[str, Any]]
) -> list[tuple[dict[str, Any], bool, bool]]:
    """The boards for the judge's list: those found, then those picked and not found
    (out of reach, or being read); each with whether it is picked and was found."""
    keys = {many.key_of(one) for one in picked}
    seen = {many.key_of(one) for one in found}
    rows = [(one, many.key_of(one) in keys, True) for one in found]
    rows += [(one, True, False) for one in picked if many.key_of(one) not in seen]
    return rows


def pick_of(board: dict[str, Any]) -> dict[str, Any]:
    """A board found as the pick keeps it: its signal, of the moment, left out."""
    return {key: value for key, value in board.items() if key != "rssi"}


def label(board: dict[str, Any], found: bool, read: bool = False) -> str:
    """A board's line in the list: its name, its link, and its signal. One the
    source reads now is not found by a search, as a board connected advertises no
    more: it is said read."""
    if board.get("link") == "ble":
        rssi = board.get("rssi")
        where = f"Bluetooth, {rssi} dBm" if found and rssi is not None else "Bluetooth"
    else:
        where = f"USB, {board.get('port') or 'the first port of its kind'}"
    state = "" if found else ", read now" if read else ", not found by the last search"
    return f"{board.get('name') or many.key_of(board)} ({where}{state})"


def run() -> int:
    """The process entry for ``--connector beam-scan``."""
    threading.Thread(target=watch_parent, args=(os.getppid(),), daemon=True).start()
    import bleak
    from serial.tools import list_ports

    return scan(sys.stdout, list_ports, bleak)
