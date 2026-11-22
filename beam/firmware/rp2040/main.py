"""The beam board on an RP2040-Zero: the light on GP2, its USB, and a BT05 on UART0.

MicroPython 1.29; flash this file as main.py and ../core/beamcore.py beside it
(README.md says how). The board logic is beamcore's; this wires it to the RP2040-Zero:
the light sensor's DO on GP2, its colour LED on GP16 (green while the light reaches
the sensor, red while it is blocked, white for FLASH), its USB serial port, and a BT05
(an HM-10 clone) on UART0, TX on GP0 to the module's RXD, RX on GP1 from its TXD: the
same lines over Bluetooth. Without a BT05 wired the board works on USB alone.

At start, while nothing is connected to it, the BT05 takes AT commands: the board finds
its baud rate and moves it to 115200 baud, where a character takes 87 us, not 1 ms, by
the module's own table of bauds; then names it beam-<last 4 hex digits of the board id>,
unless it is so named. The baud it ends at is kept in a file, for a start when the
module answers nothing (a reader still connected to it).
"""

import beamcore  # ../core/beamcore.py, flashed beside this file
import machine
import neopixel

NAME = "beam-rp2040"
SENSOR_PIN = 2  # DO of the light sensor module: high while its light is gone
LED_PIN = 16  # the board's colour LED
UART_ID, TX_PIN, RX_PIN = 0, 0, 1  # to the BT05's RXD and from its TXD
FAST, SLOW = 115200, 9600  # the baud asked of the BT05, and its own
BAUD_FILE = "bt05_baud.txt"
AT_WAIT_MS = 300  # the BT05 answers an AT command well within this
SWITCH_MS = 5000  # and at a new baud within this: the prototype's took 2.1 s
GREEN, RED, WHITE = (0, 24, 0), (24, 0, 0), (60, 60, 60)
COLOURS = {"beam": GREEN, "blocked": RED, "flash": WHITE}


class UartLink(beamcore.Link):
    """The BT05 on UART0: the characters of its Bluetooth link, at its baud rate."""

    quiet = True  # its own replies (OK, +NAME=...) are no commands: never answered

    def __init__(self, uart, baud):
        super().__init__()
        self.uart, self.baud = uart, baud

    def chars(self):
        waiting = self.uart.any()
        if not waiting:
            return ""
        return beamcore.ascii_of(self.uart.read(min(waiting, beamcore.READ_MAX)))

    def write(self, text):
        self.uart.write(text + "\r\n")

    def transfer_us(self, chars):
        return chars * 10_000_000 // self.baud  # ten bits a character

    def ready(self):
        return self.uart.txdone()


def open_uart(baud):
    return machine.UART(UART_ID, baud, tx=machine.Pin(TX_PIN), rx=machine.Pin(RX_PIN))


def ask(uart, command):
    """An AT command to the BT05, and what it answered within AT_WAIT_MS."""
    uart.read()  # whatever came before is not the answer
    uart.write(command + "\r\n")
    got = b""
    start = beamcore.ticks_us()
    while beamcore.ticks_diff(beamcore.ticks_us(), start) < AT_WAIT_MS * 1000:
        if uart.any():
            got += uart.read()
        beamcore.sleep_ms(10)
    return got


def remembered():
    try:
        with open(BAUD_FILE) as f:
            baud = int(f.read())
    except (OSError, ValueError):
        return SLOW
    return baud if baud in (FAST, SLOW) else SLOW


def remember(baud):
    """The baud kept for the next start; a flash that will not take it costs only
    that, never the board's start."""
    if baud != remembered():
        try:
            with open(BAUD_FILE, "w") as f:
                f.write(str(baud))
        except OSError:
            pass


def fast_code(uart):
    """FAST's code in the module's own baud table: four above SLOW's, which it says.
    The prototype's MLT-BT05 counts from 1200 (SLOW its 4, FAST its 8); an HM-10
    counts from 9600 (0 and 4)."""
    for char in beamcore.ascii_of(ask(uart, "AT+BAUD")):
        if char.isdigit():
            return str(int(char) + 4)
    return "4"


def answering(uart):
    """Whether the module answers on ``uart`` within SWITCH_MS: at the baud it was
    given, which it takes only seconds after its OK."""
    start = beamcore.ticks_us()
    while beamcore.ticks_diff(beamcore.ticks_us(), start) < SWITCH_MS * 1000:
        if b"OK" in ask(uart, "AT"):
            return True
    return False


def bt05(name):
    """UART0 at the BT05's baud, the module moved to FAST and named when it answers;
    at the baud remembered when it answers nothing: connected, or not there."""
    kept = remembered()
    for baud in (kept, FAST if kept == SLOW else SLOW):
        uart = open_uart(baud)
        if b"OK" in ask(uart, "AT"):
            break
    else:
        return open_uart(kept), kept
    # The baud first: after a new name the MLT-BT05 answers nothing for a second or
    # two, and a baud asked then is never taken.
    if baud == SLOW and b"OK" in ask(uart, "AT+BAUD" + fast_code(uart)):
        fast = open_uart(FAST)
        if answering(fast):
            uart, baud = fast, FAST
        else:
            uart = open_uart(SLOW)
    if name not in beamcore.ascii_of(ask(uart, "AT+NAME")):  # written only if new
        ask(uart, "AT+NAME" + name)  # best effort: a module that will not keeps its own
    remember(baud)
    return uart, baud


def board():
    board_id = "".join(f"{b:02x}" for b in machine.unique_id())
    sensor = machine.Pin(SENSOR_PIN, machine.Pin.IN, machine.Pin.PULL_UP)
    # Pulled up: a loose wire reads as a blocked beam, which the reader says, not as
    # noise, which would be phantom breaks, nor as light, none at all.
    led = neopixel.NeoPixel(machine.Pin(LED_PIN), 1)

    def show(state):
        led[0] = COLOURS[state]
        led.write()

    uart, baud = bt05("beam-" + board_id[-4:])
    links = [beamcore.UsbLink(), UartLink(uart, baud)]
    return beamcore.Board(NAME, sensor, show, links, board_id)


if __name__ == "__main__":  # on the board, as its main.py; a test imports it
    board().run()
