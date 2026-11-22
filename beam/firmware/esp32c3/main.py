"""The beam board on an ESP32-C3 SuperMini: the light on GPIO3, its USB, its Bluetooth.

MicroPython 1.29; flash this file as main.py and ../core/beamcore.py beside it
(README.md says how). The board logic is beamcore's; this wires it to the SuperMini:
the light sensor's DO on GPIO3 (no strapping pin, so the sensor cannot hold the chip in
its bootloader), the blue LED on GPIO8 (lit while the light reaches the sensor and for
FLASH), the USB serial port, and Bluetooth Low Energy of its own.

Over Bluetooth it offers the HM-10's serial service, 0xFFE0 and its characteristic
0xFFE1 (notify, and writes with or without response; the RP2040's BT05 takes only
the first), so a reader has one Bluetooth path for both boards; it is advertised as
beam-<last 4 hex digits of the board id>, again when a reader goes.
"""

import beamcore  # ../core/beamcore.py, flashed beside this file
import bluetooth
import machine

NAME = "beam-esp32c3"
SENSOR_PIN = 3  # DO of the light sensor module: high while its light is gone
LED_PIN = 8  # the board's blue LED, lit by a low pin
SERVICE, CHARACTERISTIC = 0xFFE0, 0xFFE1  # the HM-10's serial service
CHUNK = 20  # the bytes of one notification at the default ATT MTU
ADVERTISE_US = 100_000
WRITE_BUFFER = 128  # the commands written between two turns of the loop
_CONNECT, _DISCONNECT, _WRITE = 1, 2, 3  # MicroPython's BLE IRQ events


def advert(name):
    """Flags, the name, and the serial service: a reader finds the board by either."""
    encoded = name.encode()
    return (
        b"\x02\x01\x06"  # LE general discoverable, no BR/EDR
        + bytes((len(encoded) + 1, 0x09))
        + encoded
        + bytes((3, 0x03, SERVICE & 0xFF, SERVICE >> 8))
    )


class BleLink(beamcore.Link):
    """The board's own Bluetooth: the readers connected to it, the lines to them in
    notifications of CHUNK bytes, their commands from writes."""

    def __init__(self, ble, name):
        super().__init__()
        self.ble, self.name = ble, name
        self.conns = set()
        self.inbox = ""
        ble.active(True)
        ble.config(gap_name=name)
        flags = (
            bluetooth.FLAG_READ
            | bluetooth.FLAG_WRITE
            | bluetooth.FLAG_WRITE_NO_RESPONSE
            | bluetooth.FLAG_NOTIFY
        )
        char = (bluetooth.UUID(CHARACTERISTIC), flags)
        ((self.handle,),) = ble.gatts_register_services(
            ((bluetooth.UUID(SERVICE), (char,)),)
        )
        ble.gatts_set_buffer(self.handle, WRITE_BUFFER, True)  # writes appended
        ble.irq(self.event)
        self.advertise()

    def event(self, event, data):
        if event == _CONNECT:
            self.conns.add(data[0])
        elif event == _DISCONNECT:
            self.conns.discard(data[0])
            self.advertise()  # for the reader to come back, or another
        elif event == _WRITE and data[1] == self.handle:
            self.inbox += beamcore.ascii_of(self.ble.gatts_read(self.handle))

    def advertise(self):
        self.ble.gap_advertise(ADVERTISE_US, adv_data=advert(self.name))

    def chars(self):
        text, self.inbox = self.inbox, ""
        return text

    def write(self, text):
        data = (text + "\r\n").encode()
        for conn in tuple(self.conns):
            for at in range(0, len(data), CHUNK):
                try:
                    self.ble.gatts_notify(conn, self.handle, data[at : at + CHUNK])
                except OSError:
                    break  # the link is going: its reader asks RESEND once back


def board():
    board_id = "".join(f"{b:02x}" for b in machine.unique_id())
    sensor = machine.Pin(SENSOR_PIN, machine.Pin.IN, machine.Pin.PULL_UP)
    # Pulled up: a loose wire reads as a blocked beam, which the reader says, not as
    # noise, which would be phantom breaks, nor as light, none at all.
    led = machine.Pin(LED_PIN, machine.Pin.OUT, value=1)
    shown = ["blocked"]  # the light's state the LED shows, a flash aside

    def show(state):
        # One colour: lit for the light on the sensor. A flash lit as well would be no
        # flash with the laser on, so it is the other way round (contract 0.5, FLASH).
        if state == "flash":
            lit = shown[0] != "beam"
        else:
            shown[0] = state
            lit = state == "beam"
        led.value(0 if lit else 1)  # lit at a low pin

    ble = BleLink(bluetooth.BLE(), "beam-" + board_id[-4:])
    links = [beamcore.UsbLink(), ble]
    return beamcore.Board(NAME, sensor, show, links, board_id)


if __name__ == "__main__":  # on the board, as its main.py; a test imports it
    board().run()
