"""How a beam board's clock maps onto this computer's, over its cable and its radio.

Run it on every board just flashed, the prototype first and each one built after
(spec 002, FR-022), from the repository's folder, the board on USB and the chronometer
closed:

    uv run python -m beam.tools.clock_check [--port PORT] [--ble NAME] [--minutes 5]

It PINGs the board as the chronometers do, over USB and over Bluetooth at once (the
board's own name, beam- and the last 4 hex digits of its id, unless `--ble` names
another; `--ble -` for the cable alone), maps its clock anew at every answer as they
map it, and says "within" or "OUTSIDE" of each of the spec's hypotheses:

- over USB, half a round trip, the most the mapping can be off: 1 ms;
- the mapping's move from one answer to the next, what two riders a moment apart may
  differ by: 0.5 ms over USB, 3 ms over Bluetooth, for 95% of the moves;
- the board's crystal against this computer's clock: 60 ppm (the prototype's were
  +47 and -41);
- Bluetooth's mapping against the cable's at the same moments: 2 ms for 90% of the
  time. A lopsided way through the radio, the BT05's say, shows here.
"""

from __future__ import annotations

import argparse
import asyncio
import io
import itertools
import json
import queue
import statistics
import time
from dataclasses import dataclass, field
from typing import Any

from app.connectors.boards import Board, ble, esp32c3, protocol, rp2040, usb_serial
from app.connectors.boards.protocol import ClockSync, RadioSync

USB_WITHIN_MS = 1.0  # the spec's hypotheses (FR-022)
USB_MOVE_MS = 0.5
RADIO_MOVE_MS = 3.0
CRYSTAL_PPM = 60.0
RADIO_FROM_CABLE_MS = 2.0
HELLO_WAIT_S = 5.0
CONNECT_S = 30.0
RADIO_OF = {rp2040.BOARD: rp2040.RADIO, esp32c3.BOARD: esp32c3.RADIO}

Mapping = list[tuple[float, float]]  # (when here, ms; the offset, board to here, ms)


@dataclass
class Link:
    """One link's PINGs and their PONGs' trips: (sent_ms, got_ms, got_us, sent_us)."""

    radio: bool
    pinged: int = 0
    sent: dict[int, float] = field(default_factory=dict)
    trips: list[tuple[float, float, int, int]] = field(default_factory=list)

    def ping(self, sent_ms: float) -> str:
        self.pinged += 1
        self.sent[self.pinged] = sent_ms
        return f"PING {self.pinged}\n"

    def heard(self, line: str, got_ms: float) -> None:
        word, rest = protocol.parse(line)
        pong = protocol.numbers(rest, 3) if word == "PONG" else None
        if pong and (sent := self.sent.pop(pong[0], None)) is not None:
            self.trips.append((sent, got_ms, pong[1], pong[2]))

    def mapping(self) -> Mapping:
        """The offset after each answer, as a chronometer reads it from them."""
        sync = RadioSync() if self.radio else ClockSync()
        mapped = []
        for trip in self.trips:
            sync.add(*trip)
            if sync.read:
                if isinstance(sync, RadioSync):
                    mapped.append((trip[1], sync.offset))
                else:
                    mapped.append((trip[1], statistics.median(sync.offsets)))
        return mapped


def spread(values: list[float]) -> tuple[float, float]:
    """The 5th and the 95th percentiles: 90% of the values between them."""
    cuts = statistics.quantiles(values, n=20, method="inclusive")
    return cuts[0], cuts[-1]


def line_of(mapped: Mapping) -> Any:
    """The mapping's straight line: its slope the crystal's rate against this clock."""
    return statistics.linear_regression([h for h, _ in mapped], [o for _, o in mapped])


def check(what: str, value: float, limit: float, unit: str = "ms") -> str:
    verdict = "within" if abs(value) <= limit else "OUTSIDE"
    return f"  {what}: {value:.2f} {unit} ({verdict} {limit:g} {unit})"


def described(name: str, link: Link, move_limit: float) -> list[str]:
    mapped = link.mapping()
    if len(mapped) < 3:
        return [f"{name}: {len(link.trips)} answers, too few to map the clock"]
    trip = statistics.median(sum(protocol.trip(*t)) for t in link.trips)
    said = [f"{name}: {len(link.trips)} answers, a round trip {trip:.2f} ms (median)"]
    if not link.radio:  # a USB trip is short: half of it bounds the mapping
        said.append(
            check("the mapping off by at most half of it", trip / 2, USB_WITHIN_MS)
        )
    moves = [abs(b - a) for (_, a), (_, b) in itertools.pairwise(mapped)]
    said.append(
        check(
            "its move from one answer to the next, 95% under",
            spread(moves)[1],
            move_limit,
        )
        + f", the most {max(moves):.2f} ms"
    )
    ppm = -line_of(mapped).slope * 1e6  # an offset that falls: the board runs fast
    said.append(
        check("the board's crystal ahead of this clock", ppm, CRYSTAL_PPM, "ppm")
    )
    return said


def against(cable: Mapping, radio: Mapping) -> list[str]:
    """Bluetooth's mapping less the cable's straight line, at the same moments."""
    if len(cable) < 3 or len(radio) < 3:
        return []
    fit = line_of(cable)
    apart = [o - (fit.slope * here + fit.intercept) for here, o in radio]
    low, high = spread(apart)
    what = "Bluetooth's mapping from the cable's, 90% of the time"
    return [
        check(what, max(-low, high), RADIO_FROM_CABLE_MS),
        f"    {statistics.fmean(apart):+.2f} ms on average,"
        f" from {low:+.2f} to {high:+.2f}",
    ]


def report(board: str, cable: Link, radio: Link | None) -> list[str]:
    said = [f"board: {board}", *described("USB", cable, USB_MOVE_MS)]
    if radio is not None:
        said += described("Bluetooth", radio, RADIO_MOVE_MS)
        said += against(cable.mapping(), radio.mapping())
    outside = sum("OUTSIDE" in line for line in said)
    said.append(
        f"result: {outside} OUTSIDE: look at this board before it times a race"
        if outside
        else "result: every check within"
    )
    return said


def open_usb(serial: Any, port: str) -> usb_serial.Connector:
    """The board's port, the one named or the first found, opened as the chronometer
    opens it: its lines come into the connector's inbox, each timed as it came."""
    from serial.tools import list_ports

    kinds = {(kind.vendor, kind.product): kind for kind in RADIO_OF}
    for found in sorted(list_ports.comports(), key=lambda found: found.device):
        kind = kinds.get((found.vid, found.pid))
        if kind is not None and port in ("", found.device):
            out = io.StringIO()
            usb = usb_serial.Connector(out, serial, kind)
            usb.configure({"port": found.device})
            usb.open_board(time.monotonic())  # it asks HELLO
            if usb.link is None:  # the port busy, say: the chronometer still open
                said = json.loads(out.getvalue().splitlines()[-1])
                raise SystemExit(f"{found.device}: {said['detail']}")
            return usb
    raise SystemExit(f"no beam board on USB {port}".rstrip() + ": plug one in")


def hello_of(usb: usb_serial.Connector) -> list[str]:
    """The board's name, firmware, id and count, from the HELLO the opening asked."""
    end = time.monotonic() + HELLO_WAIT_S
    while (left := end - time.monotonic()) > 0:
        try:
            kind, (line, _) = usb.inbox.get(timeout=left)
        except queue.Empty:
            break
        word, rest = protocol.parse(line) if kind == "board" else ("", [])
        if word == "HELLO" and len(rest) >= 3:
            return rest
    raise SystemExit("no HELLO from the board on USB: is main.py on it?")


def open_radio(bleak: Any, kind: Board, name: str) -> ble.RadioConnector:
    """The board found by its Bluetooth name or address, connected as the
    chronometer connects it: its lines come into the connector's inbox, each timed
    by its first piece."""
    radio = ble.RadioConnector(io.StringIO(), bleak, RADIO_OF[kind])
    radio.configure({"device": name})
    try:
        found = asyncio.run_coroutine_threadsafe(radio.found(), radio.loop)
        radio.link = found.result(timeout=CONNECT_S)
    except Exception as error:
        raise SystemExit(f"Bluetooth {name}: {ble.described(error)}") from error
    return radio


def ping_for(links: list[tuple[usb_serial.Connector, Link, float]], s: float) -> str:
    """Each link PINGed at its pace for ``s`` seconds, its answers taken as they come;
    what ended it early, if anything did."""
    due = [0.0] * len(links)
    end = time.monotonic() + s
    try:
        while (now := time.monotonic()) < end:
            for at, (connector, link, every) in enumerate(links):
                if now >= due[at]:
                    connector.write(link.ping(usb_serial.now_ms()))
                    due[at] = now + every
                while not connector.inbox.empty():
                    kind, item = connector.inbox.get_nowait()
                    if kind == "lost":
                        return f"a link was lost: {item[1]}"
                    link.heard(*item)
            time.sleep(0.005)
    except KeyboardInterrupt:
        return "stopped by hand"
    return ""


def measure(serial: Any, bleak: Any, port: str, name: str, minutes: float) -> list[str]:
    """The board PINGed over each link at the chronometer's pace; then the report."""
    usb = open_usb(serial, port)
    hello = hello_of(usb)
    board = " ".join(hello[:3]) + f", USB {usb.port}"
    cable, radio = Link(radio=False), None
    links = [(usb, cable, protocol.PING_EVERY_S)]
    if name != "-":
        name = name or "beam-" + hello[2][-4:]
        radio = Link(radio=True)
        links.append(
            (open_radio(bleak, usb.spec, name), radio, protocol.RADIO_PING_EVERY_S)
        )
        board += f", Bluetooth {name}"
    try:
        stopped = ping_for(links, minutes * 60)
    finally:
        for connector, _, _ in links:
            connector.link.close()
    said = report(board, cable, radio)
    return [*said, stopped] if stopped else said


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--port", default="", help="its USB port; else the first found")
    parser.add_argument(
        "--ble", default="", help="its Bluetooth name or address; '-' for none"
    )
    parser.add_argument("--minutes", type=float, default=5.0, help="5 by default")
    args = parser.parse_args(argv)
    import bleak
    import serial

    print("\n".join(measure(serial, bleak, args.port, args.ble, args.minutes)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
