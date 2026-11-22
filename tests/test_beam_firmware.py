"""The beam boards' firmware, beam/firmware/, run on the computer.

MicroPython's modules are faked: its 30-bit microsecond ticks are a counter the
test moves on, the sensor's pin a level the test sets, and the pin's IRQ is called
on each rising edge, as the board's would be. The loop's steps are run one
millisecond at a time, as the board's own loop runs them. The core (beamcore.py)
is tested through fake links; each chip's main.py with its UART or Bluetooth faked.
"""

from __future__ import annotations

import ast
import importlib
import sys
import time
import types
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, ClassVar

import pytest

WRAP = 1 << 30  # MicroPython's ticks wrap here
FIRMWARE_DIR = Path(__file__).parents[1] / "beam" / "firmware"


class Ticks:
    """MicroPython's ticks: microseconds modulo 2**30, as the board counts them."""

    def __init__(self, start_us: int) -> None:
        self.us = start_us

    def ticks_us(self) -> int:
        return self.us % WRAP

    @staticmethod
    def ticks_diff(a: int, b: int) -> int:
        return (a - b + WRAP // 2) % WRAP - WRAP // 2

    def sleep_ms(self, ms: int) -> None:
        self.us += ms * 1000


class Pin:
    IN, OUT, PULL_UP, IRQ_RISING = 0, 1, 2, 3

    def __init__(
        self, n: int, mode: int | None = None, pull: int | None = None, value: int = 0
    ):
        self.n, self.mode, self.pull, self.level = n, mode, pull, value
        self.irqs: list[dict[str, Any]] = []

    def value(self, level: int | None = None) -> int:
        if level is not None:
            self.level = level
        return self.level

    def irq(self, **kwargs: Any) -> None:
        self.irqs.append(kwargs)


class NeoPixel(list):
    def __init__(self, pin: Pin, n: int) -> None:
        super().__init__([(0, 0, 0)] * n)

    def write(self) -> None:
        pass


class Uart:
    """UART0 with a BT05 on it: what the board writes, what the module answers. The
    module answers AT commands only at its own baud, and moves by its own table."""

    module_baud = 9600  # the BT05's, shared by every UART opened on the same wires
    answers = True  # False: connected to a reader, or not there
    codes: ClassVar[dict[str, int]] = {"4": 9600, "8": 115200}  # the MLT-BT05's
    name = "BT05"  # its advertised name, kept by the module

    def __init__(self, uart_id: int, baud: int, **pins: Any) -> None:
        self.baud, self.pins = baud, pins
        self.written: list[str] = []
        self.incoming = b""

    def write(self, text: str) -> None:
        self.written.append(text)
        command = text.strip()
        if not (Uart.answers and self.baud == Uart.module_baud):
            return
        if command == "AT+BAUD":
            code = next(c for c, baud in Uart.codes.items() if baud == self.baud)
            self.incoming += f"+BAUD={code}\r\n".encode()
        elif command.startswith("AT+BAUD"):
            code = command.removeprefix("AT+BAUD")
            self.incoming += f"+BAUD={code}\r\nOK\r\n".encode()
            Uart.module_baud = Uart.codes.get(code, Uart.module_baud)
        elif command.startswith("AT+NAME"):
            Uart.name = command.removeprefix("AT+NAME") or Uart.name
            self.incoming += f"+NAME={Uart.name}\r\n".encode()
        elif command.startswith("AT"):
            self.incoming += b"OK\r\n"

    def any(self) -> int:
        return len(self.incoming)

    def txdone(self) -> bool:
        return True

    def read(self, n: int | None = None) -> bytes | None:
        n = len(self.incoming) if n is None else n
        data, self.incoming = self.incoming[:n], self.incoming[n:]
        return data or None


class Ble:
    """MicroPython's bluetooth.BLE: what the board registers, advertises, notifies."""

    def __init__(self) -> None:
        self.adverts: list[bytes] = []
        self.notified: list[tuple[int, bytes]] = []
        self.written = b""
        self.handler: Callable[[int, tuple], None] | None = None
        self.config_kw: dict[str, Any] = {}
        self.fail_notify = False

    def active(self, on: bool) -> None:
        self.on = on

    def config(self, **kwargs: Any) -> None:
        self.config_kw.update(kwargs)

    def gatts_register_services(self, services: tuple) -> tuple:
        self.services = services
        return ((42,),)

    def gatts_set_buffer(self, handle: int, size: int, append: bool) -> None:
        self.buffer = (handle, size, append)

    def irq(self, handler: Callable[[int, tuple], None]) -> None:
        self.handler = handler

    def gap_advertise(self, interval_us: int, adv_data: bytes) -> None:
        self.adverts.append(adv_data)

    def gatts_read(self, handle: int) -> bytes:
        data, self.written = self.written, b""
        return data

    def gatts_notify(self, conn: int, handle: int, data: bytes) -> None:
        if self.fail_notify:
            raise OSError(-30)
        self.notified.append((conn, data))


def fake_modules(monkeypatch: pytest.MonkeyPatch, ticks: Ticks) -> None:
    for name in ("ticks_us", "ticks_diff", "sleep_ms"):
        monkeypatch.setattr(time, name, getattr(ticks, name), raising=False)
    machine = types.ModuleType("machine")
    vars(machine).update(
        Pin=Pin, UART=Uart, unique_id=lambda: b"\x50\x54\x31\x65\xe6\x61\x41\x03"
    )
    micropython = types.ModuleType("micropython")
    vars(micropython).update(alloc_emergency_exception_buf=lambda n: None)
    neopixel = types.ModuleType("neopixel")
    vars(neopixel).update(NeoPixel=NeoPixel)
    bluetooth = types.ModuleType("bluetooth")
    vars(bluetooth).update(
        BLE=Ble,
        UUID=lambda n: ("uuid", n),
        FLAG_READ=2,
        FLAG_WRITE_NO_RESPONSE=4,
        FLAG_WRITE=8,
        FLAG_NOTIFY=16,
    )
    for module in (machine, micropython, neopixel, bluetooth):
        monkeypatch.setitem(sys.modules, module.__name__, module)


def import_core(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.delitem(sys.modules, "beam.firmware.core.beamcore", raising=False)
    core = importlib.import_module("beam.firmware.core.beamcore")
    monkeypatch.setitem(sys.modules, "beamcore", core)  # as main.py imports it
    monkeypatch.setattr(core, "wait_us", lambda: 12_000)  # a PONG's wait, made fixed
    return core


def import_main(monkeypatch: pytest.MonkeyPatch, chip: str) -> Any:
    monkeypatch.delitem(sys.modules, f"beam.firmware.{chip}.main", raising=False)
    return importlib.import_module(f"beam.firmware.{chip}.main")


class Rig:
    """A board: its sensor's light, its clock, what it says on its two links."""

    def __init__(self, core: Any, ticks: Ticks) -> None:
        self.core, self.ticks = core, ticks
        self.shown: list[str] = []
        self.usb, self.radio = make_link(core), make_link(core, quiet=True, char_us=87)
        self.board = core.Board(
            "beam-test",
            Pin(2, Pin.IN, Pin.PULL_UP),
            self.shown.append,
            [self.usb, self.radio],
            "50543165e6614103",
        )
        self.said = self.usb.said

    def run(self, ms: int, *, blocked: bool | None = None) -> None:
        """The light blocked or not from now on, then ``ms`` of the board's loop."""
        if blocked is not None:
            self.light(blocked)
        for _ in range(ms):
            self.board.step()
            self.ticks.sleep_ms(1)

    def light(self, blocked: bool) -> None:
        pin = self.board.sensor
        if blocked and not pin.level:
            pin.level = 1
            self.core.edge(pin)  # DO rose: the IRQ, before the loop runs on
        pin.level = int(blocked)

    def chatter(self, edges: int) -> None:
        """The comparator in the half-light: the light lost and back, a ms apart."""
        for _ in range(edges):
            self.run(1, blocked=True)
            self.run(1, blocked=False)

    def breaks(self) -> list[int]:
        """The seq of each BREAK said."""
        return [int(line.split()[1]) for line in self.said if line.startswith("BREAK")]


def make_link(core: Any, *, quiet: bool = False, char_us: int = 0) -> Any:
    class FakeLink(core.Link):
        def __init__(self) -> None:
            super().__init__()
            self.quiet, self.inbox = quiet, ""
            self.said: list[str] = []

        def chars(self) -> str:
            text, self.inbox = self.inbox, ""
            return text

        def write(self, text: str) -> None:
            self.said.append(text)

        def transfer_us(self, chars: int) -> int:
            return chars * char_us

    return FakeLink()


@pytest.fixture
def rig(monkeypatch: pytest.MonkeyPatch) -> Iterator[Rig]:
    yield make_rig(monkeypatch, start_us=0)


def make_rig(monkeypatch: pytest.MonkeyPatch, start_us: int) -> Rig:
    ticks = Ticks(start_us)
    fake_modules(monkeypatch, ticks)
    return Rig(import_core(monkeypatch), ticks)


def test_a_break_is_said_with_the_time_its_edge_came(rig):
    rig.run(100, blocked=False)
    rig.ticks.us += 250  # the light goes mid-millisecond
    rig.run(5, blocked=True)
    assert [line for line in rig.said if line.startswith("BREAK")] == ["BREAK 1 100250"]
    assert rig.radio.said[-1] == "BREAK 1 100250"  # news: on every link


def test_a_bike_is_one_break_its_wheels_and_body_within_the_hold_off(rig):
    rig.run(100, blocked=False)
    for _wheel_or_body in range(3):
        rig.run(10, blocked=True)
        rig.run(200, blocked=False)
    assert rig.breaks() == [1]
    rig.run(1000, blocked=False)
    rig.run(10, blocked=True)  # the next rider
    assert rig.breaks() == [1, 2]


def test_the_light_coming_back_after_a_long_block_is_no_break(rig):
    """A rider stopped in the beam, or someone standing in it, for longer than the
    hold-off: the comparator chatters as the light comes back, and that is no rider."""
    rig.run(100, blocked=False)
    rig.run(1500, blocked=True)
    rig.chatter(5)
    rig.run(100, blocked=False)
    assert rig.breaks() == [1]
    rig.run(10, blocked=True)  # the next rider
    assert rig.breaks() == [1, 2]


def test_a_laser_first_aimed_at_the_sensor_is_no_break(rig):
    rig.run(500, blocked=True)  # the board started in the dark
    rig.chatter(5)  # the spot comes onto the sensor
    rig.run(100, blocked=False)
    assert rig.breaks() == []
    rig.run(10, blocked=True)  # then a rider
    assert rig.breaks() == [1]


def test_a_light_that_never_holds_is_said_unsteady_as_no_break_can_be_seen(rig):
    """The spot on the sensor's edge: the comparator flickers, the IRQ is never
    armed again, and the board says so instead of seeing nothing in silence."""
    rig.run(100, blocked=False)
    rig.chatter(600)  # 1.2 s of flicker
    assert rig.breaks() == [1]  # its first edge, the light lost after it held
    assert rig.said[-1] == "STATUS unsteady"
    rig.run(60, blocked=False)
    assert rig.said[-1] == "STATUS beam"


def test_the_clock_carries_on_over_the_ticks_wrapping(monkeypatch):
    """The board's ticks wrap every 18 minutes; its microseconds go on counting."""
    rig = make_rig(monkeypatch, start_us=WRAP - 600_000)
    rig.run(100, blocked=False)
    rig.run(10, blocked=True)
    rig.run(1500, blocked=False)  # the ticks wrap in here
    rig.run(10, blocked=True)
    times = [int(line.split()[2]) for line in rig.said if line.startswith("BREAK")]
    assert times == [100_000, 1_610_000]  # 100 + 10 + 1500 ms on


def test_the_board_answers_what_it_is_asked_on_the_link_that_asked(rig):
    rig.run(60, blocked=False)  # held 50 ms: said for aiming
    rig.usb.inbox = "hello\nSTATUS\nHOLDOFF 300\r\nHOLDOFF -1\nBEEP\n"
    rig.run(1)
    assert rig.said == [
        "STATUS beam",
        f"HELLO beam-test {rig.core.FIRMWARE} 50543165e6614103 0",
        "STATUS beam",
        "HOLDOFF 300",
        "ERROR unknown: HOLDOFF -1",
        "ERROR unknown: BEEP",
    ]
    assert rig.radio.said == ["STATUS beam"]  # only the news
    assert rig.board.hold_off_us == 300_000


def test_a_hello_says_the_count_of_the_last_break(rig):
    rig.run(100, blocked=False)
    rig.run(10, blocked=True)
    rig.usb.inbox = "HELLO\n"
    rig.run(1)
    assert rig.said[-1].endswith(" 50543165e6614103 1")


def test_a_pong_gives_when_its_ping_came_and_when_it_went(rig):
    """The board waits before it answers (fixed at 12 ms here), and says both of its
    moments, so the reader can leave its wait out of the round trip."""
    rig.run(10, blocked=False)
    rig.usb.inbox = "PING 7\n"
    rig.run(1)  # read at 10 ms
    assert not any(line.startswith("PONG") for line in rig.said)
    rig.run(13)
    assert rig.said[-1] == "PONG 7 10000 22000"


def test_a_ping_on_a_slow_wire_is_timed_from_its_first_character(rig):
    """On the BT05's UART a character takes its time to come: the PING began that much
    before its line ended (7 characters with the line end, 87 us each here)."""
    rig.run(10, blocked=False)
    rig.radio.inbox = "PING 9\n"
    rig.run(13)
    assert rig.radio.said[-1] == f"PONG 9 {10_000 - 7 * 87} {22_000}"
    assert not any(line.startswith("PONG") for line in rig.said)  # not on USB


def test_only_the_last_pings_of_a_flood_are_answered(rig):
    rig.usb.inbox = "".join(f"PING {n}\n" for n in range(20))
    rig.run(20)
    pongs = [line.split()[1] for line in rig.said if line.startswith("PONG")]
    assert pongs == [str(n) for n in range(12, 20)]


def test_resend_says_again_the_kept_breaks_from_a_count_on(rig):
    """A link that was down missed some breaks: the reader asks for them again."""
    rig.run(100, blocked=False)
    for _ in range(3):
        rig.run(10, blocked=True)
        rig.run(1100, blocked=False)
    rig.radio.inbox = "RESEND 2\n"
    rig.run(3)
    breaks = [line for line in rig.radio.said if line.startswith("BREAK")]
    assert breaks[-2:] == [breaks[1], breaks[2]]  # 2 and 3 again, as they were
    assert breaks[-2].startswith("BREAK 2 ")
    assert sum(line.startswith("BREAK") for line in rig.said) == 3  # USB: no again


def test_breaks_asked_for_again_go_a_line_a_turn_once_the_link_is_free(rig):
    """A long RESEND on a slow wire must never hold up the loop that arms the IRQ."""
    rig.board.kept = [(n, n * 10) for n in range(1, 6)]
    busy = [True]
    rig.radio.ready = lambda: not busy[0]
    rig.radio.inbox = "RESEND 2\n"
    rig.run(3)
    assert rig.radio.said == []  # its link still sending: they wait
    busy[0] = False
    rig.run(2)
    assert rig.radio.said == ["BREAK 2 20", "BREAK 3 30"]
    rig.run(5)
    assert rig.radio.said[-1] == "BREAK 5 50" and len(rig.radio.said) == 4
    busy[0] = True
    rig.radio.inbox = "RESEND 1\n" * 40  # a reader asking on and on
    rig.run(2)
    assert len(rig.board.resends) == rig.core.KEPT


def test_the_board_keeps_its_last_128_breaks(rig):
    rig.board.kept = [(n, n * 10) for n in range(1, 129)]
    rig.board.seq = 128
    rig.run(100, blocked=False)
    rig.run(10, blocked=True)
    assert len(rig.board.kept) == 128 and rig.board.kept[0][0] == 2


def test_a_quiet_link_gets_no_error_for_what_is_no_command(rig):
    """The BT05's own replies (OK, +NAME=...) must never be answered: the module
    would take the ERROR as another line, and the two would talk forever."""
    rig.radio.inbox = "OK\n+NAME=beam-4103\n"
    rig.run(1)
    assert rig.radio.said == []


def test_a_line_too_long_is_cut_and_a_flood_is_read_in_turns(rig):
    rig.usb.inbox = "X" * 100 + "\n"
    rig.run(1)
    assert rig.said[-1] == "ERROR unknown: " + "X" * 40
    assert rig.usb.line == ""


def test_the_led_shows_the_light_and_flashes_when_asked(rig):
    """The light reaching the sensor or blocked, for aiming; a flash for the
    cameras, then the light again."""
    rig.run(10, blocked=False)
    assert rig.shown[-1] == "beam"
    rig.run(10, blocked=True)
    assert rig.shown[-1] == "blocked"
    rig.usb.inbox = "FLASH 3\n"
    rig.run(1)
    assert rig.said[-1] == "FLASH 3 20000"
    assert rig.shown[-1] == "flash"
    rig.run(50, blocked=False)
    assert rig.shown[-1] == "flash"  # the flash goes on over the light
    rig.run(60, blocked=False)
    assert rig.shown[-1] == "beam"
    rig.usb.inbox = "FLASH\n"
    rig.run(1)
    assert rig.said[-1] == "ERROR unknown: FLASH"


def test_run_takes_the_sensor_edge_on_a_hard_irq_and_says_hello(rig, monkeypatch):
    def stop(ms: int) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(rig.core, "sleep_ms", stop)
    with pytest.raises(KeyboardInterrupt):
        rig.board.run()
    (irq,) = rig.board.sensor.irqs
    assert irq == {"handler": rig.core.edge, "trigger": Pin.IRQ_RISING, "hard": True}
    assert rig.said[0].startswith("HELLO beam-test")


def test_a_port_with_no_hard_irq_takes_the_edge_on_a_scheduled_one(rig, monkeypatch):
    """MicroPython's ESP32 port takes no hard=: the board must start all the same."""

    def irq(**kwargs: Any) -> None:
        if "hard" in kwargs:
            raise TypeError("extra keyword arguments given")
        rig.board.sensor.irqs.append(kwargs)

    def stop(ms: int) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(rig.board.sensor, "irq", irq)
    monkeypatch.setattr(rig.core, "sleep_ms", stop)
    with pytest.raises(KeyboardInterrupt):
        rig.board.run()
    assert rig.board.sensor.irqs == [
        {"handler": rig.core.edge, "trigger": Pin.IRQ_RISING}
    ]
    assert rig.said[0].startswith("HELLO beam-test")


def test_noise_on_a_link_is_read_as_question_marks_never_an_error(rig):
    assert rig.core.ascii_of(b"PI\xffNG\x00 1\r\n") == "PI?NG? 1\r\n"


def test_the_usb_link_reads_its_standard_input_a_character_at_a_time(rig, monkeypatch):
    waiting = list("PING 5\n")

    class Poll:
        def register(self, stream: object, mask: int) -> None:
            self.stream = stream

        def poll(self, timeout: int) -> list[int]:
            return [1] if waiting else []

    stdin = types.SimpleNamespace(read=lambda n: waiting.pop(0))
    monkeypatch.setattr(rig.core, "select", types.SimpleNamespace(poll=Poll, POLLIN=1))
    monkeypatch.setattr(rig.core, "sys", types.SimpleNamespace(stdin=stdin))
    printed: list[str] = []
    monkeypatch.setattr(rig.core, "print", printed.append, raising=False)
    usb = rig.core.UsbLink()
    assert usb.lines() == ["PING 5"]
    usb.write("STATUS beam")
    assert printed == ["STATUS beam"]


def test_the_random_wait_of_a_pong_stays_within_its_bound(monkeypatch):
    ticks = Ticks(0)
    fake_modules(monkeypatch, ticks)
    monkeypatch.delitem(sys.modules, "beam.firmware.core.beamcore", raising=False)
    core = importlib.import_module("beam.firmware.core.beamcore")
    waits = {core.wait_us() for _ in range(500)}
    assert all(0 <= w < core.WAIT_US for w in waits) and len(waits) > 100


@pytest.fixture
def rp2040(monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    fake_modules(monkeypatch, Ticks(0))
    import_core(monkeypatch)
    monkeypatch.setattr(Uart, "module_baud", 9600)
    monkeypatch.setattr(Uart, "answers", True)
    monkeypatch.setattr(Uart, "codes", {"4": 9600, "8": 115200})
    monkeypatch.setattr(Uart, "name", "BT05")
    monkeypatch.setattr(sys.modules["beamcore"], "UsbLink", lambda: "usb")
    yield import_main(monkeypatch, "rp2040")


def test_the_bt05_is_named_and_moved_to_115200_baud(rp2040, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # the board's own files
    uart, baud = rp2040.bt05("beam-4103")
    assert (baud, uart.baud, Uart.module_baud) == (115200, 115200, 115200)
    assert Uart.name == "beam-4103"
    assert (tmp_path / rp2040.BAUD_FILE).read_text() == "115200"
    # The next start finds it at once at the baud it remembered, its name kept.
    uart, baud = rp2040.bt05("beam-4103")
    assert baud == 115200 and uart.written == ["AT\r\n", "AT+NAME\r\n"]


def test_a_bt05_that_answers_nothing_is_taken_at_the_baud_remembered(
    rp2040, tmp_path, monkeypatch
):
    """A reader still connected to it, or no module wired: no AT command is answered,
    and the board keeps what it set the last time, or the module's own 9600."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Uart, "answers", False)
    assert rp2040.bt05("beam-4103")[1] == 9600
    (tmp_path / rp2040.BAUD_FILE).write_text("115200")
    assert rp2040.bt05("beam-4103")[1] == 115200
    (tmp_path / rp2040.BAUD_FILE).write_text("fast")
    assert rp2040.bt05("beam-4103")[1] == 9600


def test_a_flash_that_will_not_keep_the_baud_never_stops_the_start(
    rp2040, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    (tmp_path / rp2040.BAUD_FILE).mkdir()  # a file that cannot be written
    uart, baud = rp2040.bt05("beam-4103")
    assert baud == 115200 and uart.baud == 115200


def test_an_hm10_counting_its_bauds_from_9600_is_moved_by_its_own_code(
    rp2040, tmp_path, monkeypatch
):
    """An HM-10's 115200 is its 4, the prototype's MLT-BT05's 4 its 9600: the one
    code for both left that module where it was, a millisecond a character."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Uart, "codes", {"0": 9600, "4": 115200})
    assert rp2040.bt05("beam-4103")[1] == Uart.module_baud == 115200


def test_a_bt05_that_will_not_move_stays_at_its_own_baud(rp2040, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    original = Uart.write

    def no_baud(self: Uart, text: str) -> None:
        if text.strip() == "AT+BAUD8":
            self.written.append(text)
            return
        original(self, text)

    monkeypatch.setattr(Uart, "write", no_baud)
    uart, baud = rp2040.bt05("beam-4103")
    assert (baud, uart.baud) == (9600, 9600)


def test_a_bt05_that_moves_but_then_says_nothing_is_kept_at_9600(
    rp2040, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    original = Uart.write

    def silent_after(self: Uart, text: str) -> None:
        original(self, text)
        if text.strip() == "AT+BAUD8":
            Uart.answers = False

    monkeypatch.setattr(Uart, "write", silent_after)
    uart, baud = rp2040.bt05("beam-4103")
    assert (baud, uart.baud) == (9600, 9600)


def test_the_uart_link_reads_the_bt05_and_knows_its_characters_trip(rp2040):
    uart = Uart(0, 115200)
    link = rp2040.UartLink(uart, 115200)
    assert link.lines() == []
    uart.incoming = b"PING 3\r\nRESEND 4\n"
    assert link.lines() == ["PING 3", "RESEND 4"]
    link.write("PONG 3 1 2")
    assert uart.written == ["PONG 3 1 2\r\n"]
    assert link.transfer_us(7) == 607  # 7 characters at 115200 baud
    assert link.ready()  # its UART has sent all it was given
    assert rp2040.UartLink(uart, 9600).transfer_us(7) == 7291
    assert link.quiet


def test_the_rp2040_board_is_wired_as_its_readme_says(rp2040, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    board = rp2040.board()
    assert board.name == "beam-rp2040" and board.id == "50543165e6614103"
    assert (board.sensor.n, board.sensor.pull) == (2, Pin.PULL_UP)
    assert board.links[0] == "usb" and board.links[1].baud == 115200
    assert (
        board.links[1].uart.pins["tx"].n == 0 and board.links[1].uart.pins["rx"].n == 1
    )
    board.show("blocked")
    board.show("flash")
    assert rp2040.COLOURS == {
        "beam": rp2040.GREEN,
        "blocked": rp2040.RED,
        "flash": rp2040.WHITE,
    }


@pytest.fixture
def esp32c3(monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    fake_modules(monkeypatch, Ticks(0))
    import_core(monkeypatch)
    monkeypatch.setattr(sys.modules["beamcore"], "UsbLink", lambda: "usb")
    yield import_main(monkeypatch, "esp32c3")


def test_the_esp32c3_advertises_its_name_and_the_serial_service(esp32c3):
    advert = esp32c3.advert("beam-4103")
    assert advert == b"\x02\x01\x06\x0a\x09beam-4103\x03\x03\xe0\xff"
    assert len(advert) <= 31  # a BLE advertisement's room


def test_the_esp32c3_offers_the_hm10_serial_service(esp32c3):
    link = esp32c3.BleLink(Ble(), "beam-4103")
    ((service, (characteristic,)),) = link.ble.services
    assert service == ("uuid", 0xFFE0) and characteristic[0] == ("uuid", 0xFFE1)
    assert characteristic[1] == 2 | 4 | 8 | 16  # read, write both ways, notify
    assert link.ble.buffer == (42, esp32c3.WRITE_BUFFER, True)
    assert link.ble.config_kw == {"gap_name": "beam-4103"}
    assert link.ble.adverts == [esp32c3.advert("beam-4103")]


def test_the_esp32c3_takes_commands_and_sends_lines_in_20_byte_pieces(esp32c3):
    ble = Ble()
    link = esp32c3.BleLink(ble, "beam-4103")
    assert ble.handler is not None
    ble.handler(esp32c3._CONNECT, (1, 0, b""))
    ble.written = b"PING 1\nRES"
    ble.handler(esp32c3._WRITE, (1, 42))
    ble.written = b"END 2\n"
    ble.handler(esp32c3._WRITE, (1, 42))
    ble.handler(esp32c3._WRITE, (1, 7))  # another handle: not ours
    assert link.lines() == ["PING 1", "RESEND 2"]
    link.write("PONG 1 1234567890 1234599999")
    pieces = [data for _, data in ble.notified]
    assert all(len(p) <= 20 for p in pieces)
    assert b"".join(pieces) == b"PONG 1 1234567890 1234599999\r\n"
    ble.handler(esp32c3._DISCONNECT, (1, 0, b""))
    assert len(ble.adverts) == 2  # advertised again for the reader to come back
    link.write("BREAK 1 5")
    assert len(ble.notified) == len(pieces)  # nobody connected: nothing sent


def test_a_notification_that_fails_ends_that_line_not_the_board(esp32c3):
    ble = Ble()
    link = esp32c3.BleLink(ble, "beam-4103")
    ble.handler(esp32c3._CONNECT, (1, 0, b""))
    ble.fail_notify = True
    link.write("BREAK 1 5")  # no exception: the reader asks RESEND once back
    assert ble.notified == []


def test_the_esp32c3_board_is_wired_as_its_readme_says(esp32c3):
    board = esp32c3.board()
    assert board.name == "beam-esp32c3" and board.id == "50543165e6614103"
    assert (board.sensor.n, board.sensor.pull) == (3, Pin.PULL_UP)
    assert board.links[0] == "usb" and board.links[1].name == "beam-4103"


def test_the_esp32c3_led_is_lit_by_a_low_pin(esp32c3):
    board = esp32c3.board()
    (led,) = _pins_of(board)
    assert (led.n, led.mode, led.level) == (esp32c3.LED_PIN, Pin.OUT, 1)  # off
    board.show("beam")
    assert led.level == 0
    board.show("blocked")
    assert led.level == 1
    board.show("flash")
    assert led.level == 0


def _pins_of(board: Any) -> list[Pin]:
    """The Pins a board's show() closes over, found through its cell contents."""
    cells = board.show.__closure__ or ()
    return [c.cell_contents for c in cells if isinstance(c.cell_contents, Pin)]


def test_the_firmware_versions_are_one(monkeypatch):
    """Every chip runs the one core: its FIRMWARE is the version of both boards."""
    fake_modules(monkeypatch, Ticks(0))
    core = import_core(monkeypatch)
    assert core.FIRMWARE == "0.4"


@pytest.mark.parametrize(
    "path",
    sorted(FIRMWARE_DIR.rglob("*.py")),
    ids=lambda p: p.parent.name + "/" + p.name,
)
def test_the_firmware_is_python_micropython_reads(path):
    """MicroPython knows no syntax newer than about 3.8: a formatter's 3.14 style
    (PEP 758's except without parentheses) would stop the board at its start."""
    ast.parse(path.read_text(encoding="utf-8"), feature_version=(3, 8))
