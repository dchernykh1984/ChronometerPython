"""The beam board's firmware: breaks of the light on GP2, timed by the board itself.

MicroPython 1.29 on an RP2040-Zero (README.md says how to build and flash one). It
talks over its USB serial port, a line at a time; what it says:

    HELLO beam-rp2040 <firmware> <board id>
    BREAK <seq> <t_us>    the light lost: its first edge, then none until the hold-off
                          is over and the light has been back for 50 ms
    STATUS beam|blocked   the light's state once it has held 50 ms, for aiming
    STATUS unsteady       no state has held for a second: no break can be seen
    PONG <n> <t_us>       the answer to PING <n>
    FLASH <n> <t_us>      the LED lit white for FLASH <n>, for the cameras
    HOLDOFF <ms>          the hold-off in use, after HOLDOFF <ms>
    ERROR <text>          a line it did not understand

<t_us> is microseconds since the board started, on its own clock; the computer maps
it onto its own with PING. What it answers: HELLO, PING <n>, STATUS, HOLDOFF <ms>,
FLASH <n>. The LED shows the light: green while it reaches the sensor, red while it
is blocked. The contract every reader keeps to:
specs/001-event-sources/contracts/beam-board-protocol.md.
"""

import select
import sys
import time

import machine
import micropython
import neopixel

FIRMWARE = "0.3"
SENSOR_PIN = 2  # DO of the light sensor module: high while its light is gone
LED_PIN = 16  # the board's colour LED
HOLD_OFF_MS = 1000  # one rider, one break: a bike's wheels and body pass within it
SETTLE_US = 50_000  # a state said for aiming once it has held this long
UNSTEADY_US = 1_000_000  # no state held this long: the light flickers on the sensor
FLASH_US = 100_000
GREEN, RED, WHITE = (0, 24, 0), (24, 0, 0), (60, 60, 60)

ticks_us = time.ticks_us  # type: ignore[attr-defined]  # MicroPython's 30-bit clock
ticks_diff = time.ticks_diff  # type: ignore[attr-defined]
sleep_ms = time.sleep_ms  # type: ignore[attr-defined]

micropython.alloc_emergency_exception_buf(100)
_armed = False  # the next edge is a break: the loop arms it once the light is back
_at = 0  # the ticks of the last break, written in the IRQ
_taken = 0  # breaks the IRQ has taken, ever


def _edge(_pin):
    """Hard IRQ: the moment the light went, kept before anything else runs. One
    edge, then none until the loop arms it again, so the chatter of a comparator
    in the half-light never piles up, nor moves the time of the break."""
    global _armed, _at, _taken
    t = ticks_us()
    if _armed:
        _armed = False
        _at = t
        _taken += 1


class Clock:
    """Microseconds since the board started: the 30-bit ticks, which wrap every
    18 minutes, carried on as long as the loop looks at least every 9."""

    def __init__(self):
        self.last = ticks_us()
        self.us = 0

    def now(self):
        t = ticks_us()
        self.us += ticks_diff(t, self.last)
        self.last = t
        return self.us

    def of(self, ticks):
        """A recent edge's ticks as microseconds since the start."""
        return self.now() - ticks_diff(self.last, ticks)


class Board:
    def __init__(self):
        self.clock = Clock()
        # Pulled up: a loose wire reads as a blocked beam, which the computer says,
        # not as noise, which would be phantom breaks, nor as light, none at all.
        self.sensor = machine.Pin(SENSOR_PIN, machine.Pin.IN, machine.Pin.PULL_UP)
        self.led = neopixel.NeoPixel(machine.Pin(LED_PIN), 1)
        self.hold_off_us = HOLD_OFF_MS * 1000
        self.seq = 0
        self.last_break = None
        self.read = 0  # breaks said
        self.shown = None  # the state last said
        self.seen = None  # the state seen, and since when
        self.seen_at = 0
        self.held_at = 0  # when a state was last seen held
        self.flash_until = None
        self.id = "".join(f"{b:02x}" for b in machine.unique_id())

    def say(self, *words):
        print(" ".join(str(w) for w in words))

    def hello(self):
        self.say("HELLO", "beam-rp2040", FIRMWARE, self.id)

    def breaks(self):
        global _armed
        armed = _armed  # read first: unarmed, the IRQ writes nothing more
        if self.read < _taken:
            self.read = _taken
            self.seq += 1
            self.last_break = self.clock.of(_at)
            self.say("BREAK", self.seq, self.last_break)
        elif not armed and self.ready():
            _armed = True

    def ready(self):
        """The next edge may be a break: the hold-off over, and the light back for
        50 ms. The chatter of light coming back, after a rider who stopped in the
        beam or onto a laser being aimed, is then no break."""
        now = self.clock.now()
        if self.last_break is not None and now - self.last_break < self.hold_off_us:
            return False
        return self.seen == "beam" and now - self.seen_at >= SETTLE_US

    def light(self):
        state = "blocked" if self.sensor.value() else "beam"
        now = self.clock.now()
        if self.flash_until is not None and now >= self.flash_until:
            self.flash_until = None
            self.seen = None  # the LED shows the light again
        if state != self.seen:
            self.seen, self.seen_at = state, now
            if self.flash_until is None:
                self.led[0] = RED if state == "blocked" else GREEN
                self.led.write()
        if now - self.seen_at >= SETTLE_US:
            self.held_at, said = now, state
        elif now - self.held_at >= UNSTEADY_US:
            said = "unsteady"  # never armed: no break can be seen, so it is said
        else:
            return
        if said != self.shown:
            self.shown = said
            self.say("STATUS", said)

    def answer(self, line):
        words = line.split()
        command = words[0].upper() if words else ""
        if command == "PING" and len(words) == 2:
            self.say("PONG", words[1], self.clock.now())
        elif command == "HELLO":
            self.hello()
        elif command == "STATUS":
            self.say("STATUS", self.shown or "unknown")
        elif command == "HOLDOFF" and len(words) == 2 and words[1].isdigit():
            self.hold_off_us = int(words[1]) * 1000
            self.say("HOLDOFF", words[1])
        elif command == "FLASH" and len(words) == 2:
            self.led[0] = WHITE
            self.led.write()
            now = self.clock.now()
            self.flash_until = now + FLASH_US
            self.say("FLASH", words[1], now)
        elif words:
            self.say("ERROR", "unknown:", line[:40])

    def run(self):
        poll = select.poll()
        poll.register(sys.stdin, select.POLLIN)
        line = ""
        self.sensor.irq(handler=_edge, trigger=machine.Pin.IRQ_RISING, hard=True)
        self.hello()
        while True:
            self.breaks()
            self.light()
            while poll.poll(0):
                char = sys.stdin.read(1)
                if char in ("\n", "\r"):
                    if line:
                        self.answer(line)
                    line = ""
                elif len(line) < 64:
                    line += char
            sleep_ms(1)


if __name__ == "__main__":  # on the board, as its main.py; a test imports it
    Board().run()
