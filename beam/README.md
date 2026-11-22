# The beam: a laser across the finish, timed by its own board

A laser shines across the finish (or the start) onto a light sensor. The moment a rider
breaks the beam, the sensor's board stamps it with its own microsecond clock. It sends
that time to the chronometer over a USB cable or over Bluetooth, and the chronometer
moves it onto its own clock. The radio's delays of tens of milliseconds never move a
break's time (spec 002). Both chronometers read the board: this desktop one and the
Android app.

Everything for the beam is in this folder. One copy of the repository builds the same
kit every time.

| Folder | What is in it |
| --- | --- |
| [`firmware/`](firmware/README.md) | What the boards run: one core, and a `main.py` for each chip. |
| [`firmware/rp2040/`](firmware/rp2040/README.md) | The RP2040-Zero: USB, and Bluetooth through a BT05 module. |
| [`firmware/esp32c3/`](firmware/esp32c3/README.md) | The ESP32-C3 SuperMini: USB, and Bluetooth of its own. |
| [`enclosures/`](enclosures/README.md) | 3D-printed enclosures (PETG, TPU gaskets): the receiver with its lens, the laser's box, a tripod collar. |
| [`tools/`](tools/clock_check.py) | The clock check run on every board flashed: how its clock maps onto the computer's, over USB and Bluetooth. |

What the boards say, and what a program reading them does, is one contract:
[`specs/001-event-sources/contracts/beam-board-protocol.md`](../specs/001-event-sources/contracts/beam-board-protocol.md).

## The two kits

Both work over a USB cable and over Bluetooth. A kit is a receiver on one side of the
course and an emitter on the other, each on its own USB-C power bank: every part of the
judging system is powered over USB-C. The receiver is a board with Bluetooth, the ESP32-C3
SuperMini whose own chip has it (kit 2) or the RP2040-Zero with a BT05 (kit 1), and the
light sensor behind the lens. The emitter is the laser on a USB-C power module and nothing
else: it only shines, with no wire to the receiver.

| Part | Kit 1 | Kit 2 | Price, KZT | Where |
| --- | --- | --- | --- | --- |
| Board | RP2040-Zero | ESP32-C3 SuperMini | 2,458 (the ESP32-C3) | Ozon |
| Bluetooth | BT05 (AT-09, an HM-10 clone on the CC2541) | on the board | 2,480 (the BT05) | Ozon |
| Light sensor | LM393 module with a photoresistor, 3 pins (VCC, GND, DO) | the same, 4 pins (VCC, GND, DO, AO) | 689 | Ozon |
| Lens | a 3x hand magnifier's 60 mm lens | the same | about 1,000 to 2,000 | not bought yet |
| Laser | KY-008, 650 nm, 5 V | the same | 787 | Ozon |
| Laser's power | a USB-C power module with 5.1 kOhm from CC1 and CC2 to GND (below) | the same | about 550 | not bought yet |
| Dupont wires, female-female | 3 for the sensor, 4 for the BT05 | 3 for the sensor | | |
| USB-C cables and power banks | one for the receiver, one for the emitter, with a low-current mode (below) | the same | | |

**The laser's power module.** Any USB-C board that brings its VBUS and GND out to pins, with
a 5.1 kOhm resistor from each of CC1 and CC2 to GND: without them a USB-C power bank or
charger gives it no 5 V (a USB-A to C cable does). Documented ones: SparkFun's USB 2.0
Type-C Connector Breakout (BOB-17110), Pololu's USB 2.0 Type-C Connector Breakout (usb07a),
Adafruit's USB-C Breakout Board, Downstream Connection (4090). A local one, Kaspi's "Type-C
power module" (5 V, 12 x 10 x 5 mm, 550 KZT), does not say: on one that has them a meter
reads 5.1 kOhm from each CC pin to GND, 10.2 between the two. VBUS goes to the laser's `S`,
GND to its `-`. Until one is bought, a board's 5 V powers the laser on the table (the
Sensor Shield's `V` and `G` rows).

**The power banks.** A laser draws 20 to 40 mA and a receiver 30 to 80: less than many power
banks need to stay on, and they switch themselves off within a minute. A low-current mode
(Xiaomi's and Anker's: two presses of the button) ends by itself after 2 hours, short of a
race day. So run each power bank with its load on the table for as long as a race lasts;
one that switches off gets a load beside the laser, a 47 Ohm 1 W resistor from VBUS to GND
(about 100 mA, still over 40 hours from 10,000 mAh), or is not used.

Kit 1's board, sensor and laser were bought before this list was kept. The enclosures, the
screws and the tripods are listed in [`enclosures/README.md`](enclosures/README.md). A
beam's emitter, receiver and lens come to about 3,500 KZT, under the spec's limit of
10,000 (FR-020).

Do not buy an HC-05 or an HC-06: they are Bluetooth Classic, which neither chronometer
reads. A BT05, AT-09, MLT-BT05 or a genuine HM-10 is Bluetooth Low Energy, which they do.

## Building one

1. **Wire it.** The chip's README has the pins:
   [RP2040-Zero](firmware/rp2040/README.md#wiring),
   [ESP32-C3](firmware/esp32c3/README.md#wiring).
2. **Flash it.** Put MicroPython on the board once, then copy two files onto it: the chip's
   `main.py` and `firmware/core/beamcore.py`. The chip's README has the commands.
3. **Check its clock.** With the board on USB and the chronometer closed, from the
   repository's folder: `uv run python -m beam.tools.clock_check`. For 5 minutes it PINGs
   the board over USB and Bluetooth at once, then says each of spec 002's hypotheses
   (FR-022) within or OUTSIDE, and last `result: every check within`. Every board, each
   time it is flashed: one with a line OUTSIDE is looked at before it times a race.
4. **Set the sensor.** The sensor module has two LEDs: power, and one that lights while
   light reaches the sensor. Turn its trimmer until that LED is just lit in the light the
   sensor will see, and goes out when the sensor is covered. Behind the lens, the
   laser's focused spot is far brighter than daylight, so there is room on either side.
5. **Enclose it** ([`enclosures/README.md`](enclosures/README.md)), and set it up: the
   receiver and the emitter on tripods, 10 to 12 m apart. Aim the laser at the lens until
   the board's LED shows the light on the sensor.

## In the desktop chronometer

1. Choose the results file: every break also goes to the beam's own file next to it,
   `<results>.beam_breaks.txt`.
2. Event source: Source `beam`, Device one of these:

   | Device | The board | Its link |
   | --- | --- | --- |
   | `Beam board RP2040 (USB)` | RP2040-Zero | its USB cable |
   | `Beam board RP2040 + BT05 (Bluetooth)` | RP2040-Zero | its BT05 |
   | `Beam board ESP32-C3 (USB)` | ESP32-C3 SuperMini | its USB cable |
   | `Beam board ESP32-C3 (Bluetooth)` | ESP32-C3 SuperMini | its own Bluetooth |

3. Beam records: `Rider cutoffs` for the finish, `Group starts` for the start.
4. Settings, the JSON in the Settings field:

   | Setting | Default | What |
   | --- | --- | --- |
   | `device` (Bluetooth) | `""` | The board's name, `beam-` and the last 4 hex digits of its id, or its address. Named none, the chronometer says the boards in range and reads none. |
   | `port` (USB) | `""`: the first port with the board's USB ids | `/dev/cu.usbmodem101`, `COM5`: for two boards on one computer. |
   | `hold_off_ms` | 1000 | After a break, edges this soon are the same rider's: a bike's wheels and body. 1 to 60000. |

5. Start. The action log says `source connecting beam-4103 (Bluetooth)` (or the USB
   port), then `source connected beam-esp32c3 0.4 <board id>`. Cover the sensor:
   the break comes in at the bottom slot, with the number typed in Next, as a hand cutoff
   does. For group starts, the first break after a group is chosen is its start.

To find a board's name, start with `device` empty: the log says the boards in range. A
BT05 is renamed `beam-` and its board's digits at the board's start. One that will not take
the name keeps its own (`BT05`, `MLT-BT05`): use that, or its address.

The first time on a Mac, macOS asks whether the chronometer may use Bluetooth: Allow. On
Linux, the `bluetooth` service has to run.

## In the Android app

Device `USB beam` reads either board on the phone's USB (an OTG adapter or a USB-C
cable). Device `Bluetooth beam` reads either one over Bluetooth, by the same name. The
app's own help says more.

## When the log says

| The log says | Why |
| --- | --- |
| `source disconnected name the board in Settings, as {"device": "beam-1a2b"}; in range: ...` | No board named: copy one of those into Settings. |
| `source disconnected no Bluetooth beam board in range` | The board is off, out of range, or still connected to another program, a phone say. |
| `source disconnected no Beam board ... named '...' in range` | The name is wrong, or the board is off or out of range. It tries again every 2 s. |
| `source disconnected the board's Bluetooth link was lost: ...` | Out of range, or switched off. It comes back by itself; the breaks the board saw meanwhile come then, with their own times. |
| `source disconnected Bluetooth device is turned off` | The computer's Bluetooth is off: switch it on. |
| `source disconnected no Beam board ... (USB) found on USB` | Not plugged in, a charge-only cable, or the board is in its bootloader. On a Mac with Apple silicon, the question whether to allow the accessory may still wait for its answer: Allow. |
| `source disconnected [Errno 13] could not open port ...: Permission denied` | Linux: only the `dialout` group may open serial ports. `sudo usermod -aG dialout $USER`, then log out and in. |
| `source disconnected ... Could not exclusively lock port ...` | Another chronometer has the board: one board, one chronometer. |
| `source connected ...: the beam is blocked: no break can be seen until the light is back` | Blocked for over 2 s, longer than any rider takes: the laser is off the lens, someone stands in the beam, or a sensor wire is loose. |
| `source connected ...: the light flickers on the sensor: no break can be seen; aim it again` | No state of the light has held 50 ms for about 3 s: the spot sits on the sensor's edge. Focus the lens (the enclosures' README). |
| `source error: the board runs firmware 0.3, the chronometer reads 0.4: ...` | The board has older files than this chronometer reads: copy them again (the chip's README). |
| `source error: the board's break(s) 6 to 7 did not arrive: ...` | The link was down while the board saw riders, and it no longer keeps them (it keeps its last 128): check those finishes by other means. |
| `source error: the board's clock could not be read: ...` | No PING was answered in time: the breaks are timed by when they came, which over Bluetooth may be tens of ms late. |
| `source disconnected the board answers no PING: is main.py running on it?` | The board runs no `main.py`, or it stopped: power it off and on; if it says so again, copy the files again. |

## Accuracy

The board stamps a break within a fraction of a millisecond: the RP2040 in a hard
interrupt, the ESP32-C3 in a scheduled one (its MicroPython has no other), which a garbage
collection may hold up to 1.2 ms. The chronometer maps the board's clock onto its own anew
at every answer to its PINGs, never once for the race: over USB from the median of the
last 9; over Bluetooth from the shortest trip each way of the last 32, a PING every 0.5 s
(spec 002, FR-002).
So the mapping may move a little from one rider to the next, but its error never piles up
with the crystal's drift (the prototype's: about +46 and -41 ppm, 150 to 170 ms an hour), and a
link that came back is read again by itself.

The clock check (step 3 of Building one) measures this on every board: the cable's
mapping, which half a round trip bounds; its move from one answer to the next; the
crystal's rate; and Bluetooth's mapping against the cable's at the same moments, where
Kit 1's BT05 shows if its UART makes one way longer than the other (the board counts its
characters' time both ways). The prototype's, warm, read by a Mac (task T022, 2026-11-22):

| | Kit 1: RP2040 + BT05 | Kit 2: ESP32-C3 |
| --- | --- | --- |
| USB round trip, median; half of it, the most the mapping can be off | 4.9 ms; 2.5 ms | 4.2 ms; 2.1 ms |
| USB mapping's move from one answer to the next, 95% | 0.32 ms | 0.31 ms |
| Crystal against the Mac's clock | +46 ppm | -42 ppm |
| Bluetooth round trip, median | 43 ms | 43 ms |
| Bluetooth mapping's move from one answer to the next, 95%; most | 0.50 ms; 2.5 ms | 0.62 ms; 2.4 ms |
| Bluetooth's mapping from the cable's: on average; 90% within | +0.16 ms; 1.7 ms | +0.40 ms; 1.8 ms |
| A break's interrupt after its edge: median; most | 63 us; 78 us | 53 us; 165 us, 1.2 ms in a garbage collection |

So a break's time is off by about half a millisecond as a rule: 9 in 10 within 1.8 ms over
Bluetooth, and over USB within 2.5 ms at most (half a round trip; the cable's and the radio's
mappings agree within 0.5 ms on average). A rider's time, a start's error and a finish's
together, holds to a hundredth of a second, never to a thousandth: results are given in
hundredths. The light sensor's own delay comes on top, the same at both ends when both are
beams; the falling weight measures it (T015). The same after an hour in the cold is still to
be measured (T022). The field test then
times real breaks: two kits, one beam 0.5 m under the other, and a weight dropped from
rest above them (SC-010, task T015).
