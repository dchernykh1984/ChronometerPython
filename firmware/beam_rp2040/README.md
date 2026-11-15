# Beam board: an RP2040-Zero, a light sensor and a laser

A light beam across the finish line for the chronometer. The board times each break
of the light with its own microsecond clock and reports it over USB; `connector.py`
moves that time onto the computer's clock and hands the break to the chronometer,
which stamps the next empty slot with it.

Everything the board runs is in this folder, at the versions below: one copy of the
repository gives the same board, every time.

| File | What it is |
| --- | --- |
| `main.py` | The board's firmware: exactly the file copied onto the board. |
| `connector.py` | The program the chronometer starts: the board to the chronometer. |
| `connector.py.lock` | Its dependencies, locked (`uv lock --script connector.py`). |

## Versions

| What | Version | Pinned in |
| --- | --- | --- |
| MicroPython | v1.29.0, build `RPI_PICO` | this file, with its SHA-256 |
| mpremote (copies files to the board) | 1.29.0 | the commands below |
| Firmware | 0.3 | `FIRMWARE` in `main.py`; the board says it in its `HELLO` |
| Python for the connector | 3.14 | the script block at the top of `connector.py` |
| pyserial | 3.5 | the script block and `connector.py.lock` |

## Parts

| Part | Notes |
| --- | --- |
| RP2040-Zero (Waveshare, or a clone) | Tested on a "V1083" clone: USB-C, a colour LED on GP16. |
| Light sensor module | LM393 comparator, a photoresistor and a trimmer; pins VCC, GND, DO, AO. |
| KY-008 laser module | 650 nm, 5 V. Not needed to try the board: a finger over the sensor will do. |
| Pin headers | 2 x 9 for the long rows, 1 x 5 for the short edge if wanted. |
| Dupont wires, female-female | 3 for the sensor, 2 for the laser. |
| USB-C cable | One that carries data, not a charge-only one. |

Solder the headers with their long pins out on the side with the pin labels, so the
labels stay readable while wiring.

## Wiring

Hold the board with its labels facing you and the USB socket up. The left row, from
the USB end: `5V`, `GND`, `3V3`, `29`, `28`, `27`, `26`, `15`, `14`. The right row,
from the USB end: `GP0`, `GP1`, `GP2`, and on.

| Module pin | Board pin | Why |
| --- | --- | --- |
| Sensor `VCC` | `3V3` | Not 5V: `DO` swings up to `VCC`, and a GP pin takes 3.3 V at most. |
| Sensor `GND` | `GND` | |
| Sensor `DO` | `GP2` (right row, third from USB) | High while the light is gone. Pulled up on the board: a loose wire reads as a blocked beam, which the log says. |
| Sensor `AO` | - | Not used. |
| Laser `S` | `5V` | The laser lights whenever the board has power. |
| Laser `-` | `GND` | The board has one `GND` pin: share it with a Y wire, or power the laser from its own 5 V supply. |
| Laser middle pin | - | Not used. |

The sensor module has two LEDs: power, and one that lights while light reaches the
sensor. Turn its trimmer until that LED is just lit in the light the sensor will
see (the room's, or the laser's spot), and goes out when the sensor is covered.

## Flashing

1. Download MicroPython and check it:

   ```bash
   curl -LO https://micropython.org/resources/firmware/RPI_PICO-20260824-v1.29.0.uf2
   shasum -a 256 RPI_PICO-20260824-v1.29.0.uf2
   # e1160e602e277d85920adb5fe741435edccba9ba6ecadc85fdab75252eeff4e9
   ```

2. Hold `BOOT`, plug the board in, let go: a drive `RPI-RP2` appears (a board with
   an empty flash shows it without `BOOT`). Copy the `.uf2` onto it; the board
   restarts as MicroPython and the drive goes.
3. Copy the firmware, from the repository's folder:

   ```bash
   uvx mpremote@1.29.0 connect auto cp firmware/beam_rp2040/main.py :main.py + reset
   ```

   The board's LED turns green, and red while the sensor is covered. The same
   command puts a new `main.py` on later; MicroPython itself stays.

4. Check it (optional): `uvx mpremote@1.29.0 connect auto repl`, type `HELLO` and
   Enter (what is typed is not shown), cover the sensor; `Ctrl-]` leaves. What it
   should say:

   ```text
   HELLO beam-rp2040 0.3 5054316551247c1c
   BREAK 1 18734215
   STATUS blocked
   STATUS beam
   ```

`Ctrl-C` in that window stops `main.py`; unplugging the board and plugging it in
again starts it.

## In the chronometer

1. Choose the results file: every break also goes to the beam's own file next to
   it, `<results>.beam_breaks.txt`.
2. Event source: Source `beam`, Device `Custom command`.
3. Settings, the command line, with full paths (a program started from Finder or
   a desktop shortcut does not get the terminal's `PATH`; `which uv` or `where uv`
   tells where uv is):

   ```text
   /opt/homebrew/bin/uv run --script /path/to/WindowsChronometerPython/firmware/beam_rp2040/connector.py
   ```

   On Windows, `C:\Users\<you>\.local\bin\uv.exe run --script C:\path\to\...\connector.py`.
   A path with spaces goes in double quotes.

   The first start fetches Python 3.14 and pyserial into uv's cache, which takes
   the network: run the command once with `--help` after it, at home, and the
   race needs none.

4. Start. The action log says `source connecting /dev/cu.usbmodem101`, then
   `source connected beam-rp2040 0.3 <board id>`. Cover the sensor: a slot takes
   the time.

The connector's options go after `connector.py`:

| Option | Default | What |
| --- | --- | --- |
| `--port P` | the first MicroPython RP2040 port (USB 2E8A:0005) | `/dev/cu.usbmodem101`, `COM5`: for two boards on one computer. |
| `--hold-off-ms N` | 1000 | After a break, edges this soon are the same rider's: a bike's wheels and body. 1 to 60000. The next break also waits for the light to be back for 50 ms, so light coming back after a long block, or a laser being aimed, is no break. |

| The log says | Why |
| --- | --- |
| `source disconnected no beam board found on USB` | Not plugged in, a charge-only cable, or the board is in `RPI-RP2` mode. On a Mac with Apple silicon, the question whether to allow the accessory may still wait for its answer: Allow. It tries again every 2 s. |
| `source disconnected [Errno 13] could not open port /dev/ttyACM0: ... Permission denied` | Linux: only the `dialout` group may open serial ports. `sudo usermod -aG dialout $USER`, then log out and in. |
| `source disconnected ... Could not exclusively lock port ...` | Another chronometer has the board: one board, one chronometer. |
| Breaks missing, lines garbled | Another program has the port open too: an `mpremote` window, a serial monitor. Close it. |
| `source connected ...: the beam is blocked: no break can be seen until the light is back` | Blocked for over 2 s, longer than any rider takes: the laser is off the sensor, someone stands in the beam, or a sensor wire is loose. The same line without it follows once the light is back. |
| `source connected ...: the light flickers on the sensor: no break can be seen; aim it again` | For about 3 s no state of the light has held 50 ms (the board says so after 1 s, the connector after 2 s more): the spot sits on the sensor's edge. |
| `source error: the board runs firmware 0.2, main.py here is 0.3: ...` | The board has another `main.py` than this folder: copy it (Flashing, step 3). |
| `source error: the board's break(s) 6 to 7 did not arrive: ...` | The USB link was down for a moment, the board's power not, and it saw riders meanwhile: check those finishes by other means. |
| `source disconnected the board answers no PING: is main.py running on it?` | The board runs no `main.py`, or it has stopped: unplug the board and plug it in again; if it says so again, copy `main.py` again (Flashing, step 3). |

## What the board says

Its lines, when a break is a break, and what a program reading the board does (this
connector, and the Android app's USB beam alike) are in one contract:
[`specs/001-event-sources/contracts/beam-board-protocol.md`](../../specs/001-event-sources/contracts/beam-board-protocol.md).

## Out of doors

A bare sensor works for a finger, not for a laser 10 m away: a 0.06 degree tilt of
its stand moves the spot by 1 cm, more than the photoresistor is wide, so wind or a
flexing ramp would break the beam at every gust. The spot has to land on a lens or a
reflector that catches it wherever it wanders over a few centimetres (spec FR-019,
research 11). The firmware stays as it is.
