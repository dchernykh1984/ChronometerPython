"""The beam board's logic, the same on every chip: breaks of the light, timed by it.

A chip's main.py (rp2040/, esp32c3/) builds a Board from its sensor pin, its LED and
its links, and runs it; flashing copies this file beside it as beamcore.py. What a
board says and answers is the contract every reader keeps to:
specs/001-event-sources/contracts/beam-board-protocol.md.

    HELLO <name> <firmware> <board id> <seq>
    BREAK <seq> <t_us>    the light lost: its first edge, then none until the hold-off
                          is over and the light has been back for 50 ms
    STATUS beam|blocked   the light's state once it has held 50 ms, for aiming
    STATUS unsteady       no state has held for a second: no break can be seen
    PONG <n> <got_us> <sent_us>   PING <n>: when it came, and when this answer went
    FLASH <n> <t_us>      the LED lit for FLASH <n>, for the cameras
    HOLDOFF <ms>          the hold-off in use, after HOLDOFF <ms>
    ERROR <text>          a line it did not understand

<t_us> is microseconds since the board started, on its own clock; a reader maps it onto
its own with PING. The board answers HELLO, PING <n>, STATUS, HOLDOFF <ms>, FLASH <n>
and RESEND <seq> (its last 128 breaks from that count on, said again). An answer goes
back on the link the command came from; a BREAK, a change of STATUS and the HELLO at
start go on every link.
"""

import random
import select
import sys
import time

import machine
import micropython

FIRMWARE = "0.4"
HOLD_OFF_MS = 1000  # one rider, one break: a bike's wheels and body pass within it
SETTLE_US = 50_000  # a state said for aiming once it has held this long
UNSTEADY_US = 1_000_000  # no state held this long: the light flickers on the sensor
FLASH_US = 100_000
KEPT = 128  # breaks kept, to be said again on RESEND after a link came back
WAIT_US = (
    50_000  # a PONG waits up to this: its answer falls anywhere between radio events
)
PONGS_MAX = 8  # PONGs waiting their turn; a flood of PINGs keeps only the last
PIECE = 20  # the characters a BT05 holds before it sends them as one notification
LINE_MAX = 64
READ_MAX = 256  # characters read from a link in one turn of the loop

ticks_us = time.ticks_us  # type: ignore[attr-defined]  # MicroPython's 30-bit clock
ticks_diff = time.ticks_diff  # type: ignore[attr-defined]
sleep_ms = time.sleep_ms  # type: ignore[attr-defined]

micropython.alloc_emergency_exception_buf(100)
_armed = False  # the next edge is a break: the loop arms it once the light is back
_at = 0  # the ticks of the last break, written in the IRQ
_taken = 0  # breaks the IRQ has taken, ever


def edge(_pin):
    """Hard IRQ: the moment the light went, kept before anything else runs. One
    edge, then none until the loop arms it again, so the chatter of a comparator
    in the half-light never piles up, nor moves the time of the break."""
    global _armed, _at, _taken
    t = ticks_us()
    if _armed:
        _armed = False
        _at = t
        _taken += 1


def wait_us():
    """A PONG's random wait, 0 to WAIT_US: over Bluetooth an answer sent at once
    would always wait a whole connection event, and the reader needs some that
    do not, to see the way back at its shortest."""
    return random.getrandbits(16) * WAIT_US >> 16


def ascii_of(data):
    """Bytes from a link as text: anything not printable ASCII as '?', never an
    error, whatever noise a wire or a radio brings."""
    return "".join(chr(b) if 32 <= b < 127 or b in (10, 13) else "?" for b in data)


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


class Link:
    """A way to a reader: characters in, lines out. A chip's main gives its own."""

    quiet = False  # True: a line that is no command gets no ERROR back

    def __init__(self):
        self.line = ""

    def chars(self):
        """The characters come in since last asked."""
        return ""

    def write(self, text):
        """One line out, its end added."""

    def transfer_us(self, chars):
        """How long ``chars`` characters take to come in on this link, when known."""
        return 0

    def ready(self):
        """Whether a line written now goes at once, not after the ones before it."""
        return True

    def lines(self):
        """The lines ended since last asked; a line longer than LINE_MAX is cut."""
        ended = []
        for char in self.chars():
            if char in "\r\n":
                if self.line:
                    ended.append(self.line)
                self.line = ""
            elif len(self.line) < LINE_MAX:
                self.line += char
        return ended


class UsbLink(Link):
    """The USB serial port: MicroPython's own standard input and output."""

    def __init__(self):
        super().__init__()
        self.poll = select.poll()
        self.poll.register(sys.stdin, select.POLLIN)

    def chars(self):
        text = ""
        while len(text) < READ_MAX and self.poll.poll(0):
            text += sys.stdin.read(1)
        return text

    def write(self, text):
        print(text)


class Board:
    """One board: its sensor (high while the light is gone), ``show`` lighting its
    LED for "beam", "blocked" or "flash", and its links to the readers."""

    def __init__(self, name, sensor, show, links, board_id):
        self.name, self.sensor, self.show, self.links = name, sensor, show, links
        self.id = board_id
        self.clock = Clock()
        self.hold_off_us = HOLD_OFF_MS * 1000
        self.seq = 0
        self.last_break = None
        self.read = 0  # breaks said
        self.shown = None  # the state last said
        self.seen = None  # the state seen, and since when
        self.seen_at = 0
        self.held_at = 0  # when a state was last seen held
        self.flash_until = None
        self.kept = []  # (seq, t_us) of the last KEPT breaks
        self.pongs = []  # (due_us, link, n, got_us): PONGs waiting their turn
        self.resends = []  # (link, line): breaks asked for again, a line a turn

    def say(self, *words):
        """News, on every link."""
        text = " ".join(str(w) for w in words)
        for link in self.links:
            link.write(text)

    def hello(self, link=None):
        words = ("HELLO", self.name, FIRMWARE, self.id, self.seq)
        if link is None:
            self.say(*words)
        else:
            link.write(" ".join(str(w) for w in words))

    def breaks(self):
        global _armed
        armed = _armed  # read first: unarmed, the IRQ writes nothing more
        if self.read < _taken:
            self.read = _taken
            self.seq += 1
            self.last_break = self.clock.of(_at)
            self.kept.append((self.seq, self.last_break))
            del self.kept[:-KEPT]
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
                self.show(state)
        if now - self.seen_at >= SETTLE_US:
            self.held_at, said = now, state
        elif now - self.held_at >= UNSTEADY_US:
            said = "unsteady"  # never armed: no break can be seen, so it is said
        else:
            return
        if said != self.shown:
            self.shown = said
            self.say("STATUS", said)

    def answer(self, link, line):
        """One command, from ``link``; what it asks goes back on that link."""
        words = line.split()
        command = words[0].upper() if words else ""
        reply = link.write
        if command == "PING" and len(words) == 2:
            # Its first character's moment: its line end, less the characters' own
            # trip where the link knows it (the BT05's UART, at about 1 ms each).
            got = self.clock.now() - link.transfer_us(len(line) + 1)
            self.pongs.append((got + wait_us(), link, words[1], got))
            del self.pongs[:-PONGS_MAX]
        elif command == "HELLO":
            self.hello(link)
        elif command == "STATUS":
            reply("STATUS " + (self.shown or "unknown"))
        elif command == "HOLDOFF" and len(words) == 2 and words[1].isdigit():
            self.hold_off_us = int(words[1]) * 1000
            reply("HOLDOFF " + words[1])
        elif command == "FLASH" and len(words) == 2:
            self.show("flash")
            now = self.clock.now()
            self.flash_until = now + FLASH_US
            reply(f"FLASH {words[1]} {now}")
        elif command == "RESEND" and len(words) == 2 and words[1].isdigit():
            # A line a turn, and only once the link has sent the last: 128 lines at 9600
            # baud would hold the loop 3 s, and an edge after the hold-off goes unseen
            # while the loop that arms the IRQ again waits.
            first = int(words[1])
            again = [f"BREAK {s} {t}" for s, t in self.kept if s >= first]
            self.resends += [(link, line) for line in again]
            del self.resends[:-KEPT]  # asked again and again: the last asks are enough
        elif words and not link.quiet:
            reply("ERROR unknown: " + line[:40])

    def answers(self):
        """The PONGs whose wait is over, each timed as it goes."""
        now = self.clock.now()
        if not any(due <= now for due, _, _, _ in self.pongs):
            return
        due = [p for p in self.pongs if p[0] <= now]
        self.pongs = [p for p in self.pongs if p[0] > now]
        for _, link, n, got in due:
            # Timed as its first piece leaves the link: a BT05 sends nothing before its
            # UART has carried 20 characters, 1.7 ms at 115200, which no PING waits.
            link.write(f"PONG {n} {got} {self.clock.now() + link.transfer_us(PIECE)}")

    def resent(self):
        """The next break asked for again, once its link is free."""
        if self.resends and self.resends[0][0].ready():
            link, line = self.resends.pop(0)
            link.write(line)

    def step(self):
        """One turn of the loop: breaks, the light, commands, answers due."""
        self.breaks()
        self.light()
        for link in self.links:
            for line in link.lines():
                self.answer(link, line)
        self.answers()
        self.resent()

    def run(self):
        try:
            self.sensor.irq(handler=edge, trigger=machine.Pin.IRQ_RISING, hard=True)
        except TypeError:  # the ESP32 port has no hard pin IRQ: a scheduled one
            self.sensor.irq(handler=edge, trigger=machine.Pin.IRQ_RISING)
        self.hello()
        while True:
            self.step()
            sleep_ms(1)
