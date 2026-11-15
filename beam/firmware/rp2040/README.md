# The RP2040-Zero beam board

The RP2040-Zero (Waveshare, or a clone) times the beam's breaks. It reports them over its
USB cable, and over Bluetooth through a BT05 module on its UART. Without a BT05 wired, it
works on USB alone. [`../../README.md`](../../README.md) has the kits, the chronometers'
settings and what their log says.

## Parts

| Part | Notes |
| --- | --- |
| RP2040-Zero | Tested on a "V1083" clone: USB-C, a colour LED on GP16. |
| Light sensor module | LM393 comparator, a photoresistor and a trimmer; pins VCC, GND, DO (and AO). |
| BT05 | Or AT-09, MLT-BT05, HM-10: Bluetooth Low Energy, 6 pins; VCC takes 3.6 to 6 V. |
| KY-008 laser module | 650 nm, 5 V, on the other side of the course, on its own power. |
| Pin headers | 2 x 9 for the long rows. |
| Dupont wires, female-female | 3 for the sensor, 4 for the BT05, 2 for the laser while trying it on the table. |

Solder the headers with their long pins out on the side with the pin labels, so the
labels stay readable while wiring.

## Wiring

Hold the board with its labels facing you and the USB socket up. The left row, from the
USB end: `5V`, `GND`, `3V3`, `29`, `28`, `27`, `26`, `15`, `14`. The right row, from the USB
end: `GP0`, `GP1`, `GP2`, and on.

| Module pin | Board pin | Why |
| --- | --- | --- |
| Sensor `VCC` | `3V3` | Not 5V: `DO` swings up to `VCC`, and a GP pin takes 3.3 V at most. |
| Sensor `GND` | `GND` | |
| Sensor `DO` | `GP2` (right row, third from USB) | High while the light is gone. Pulled up on the board: a loose wire reads as a blocked beam, which the log says. |
| BT05 `VCC` | `5V` | Its own regulator makes its 3.3 V. |
| BT05 `GND` | `GND` | |
| BT05 `RXD` | `GP0` (right row, first) | The board's UART0 TX: 3.3 V, which the BT05 takes. |
| BT05 `TXD` | `GP1` (right row, second) | The board's UART0 RX. |
| BT05 `STATE`, `EN` | - | Not used. |
| Laser `S` | `5V` | On the table only: at a race the laser has its own power bank. |
| Laser `-` | `GND` | |

The board has one `GND` pin: the sensor, the BT05 (and the laser on the table) share it
through a Y wire or a small breadboard.

At start, while nothing is connected to it, the BT05 takes AT commands. The board finds
its baud rate, names it `beam-` and the last 4 hex digits of the board id, and moves it to
115200 baud, where a character takes 87 us instead of 1 ms. The baud it ends at is kept in
`bt05_baud.txt` on the board, for a start when a reader is still connected to the module.
A module that will not take the name keeps its own: the chronometers find it by that.

## Flashing

1. Download MicroPython and check it:

   ```bash
   curl -LO https://micropython.org/resources/firmware/RPI_PICO-20260824-v1.29.0.uf2
   shasum -a 256 RPI_PICO-20260824-v1.29.0.uf2
   # e1160e602e277d85920adb5fe741435edccba9ba6ecadc85fdab75252eeff4e9
   ```

2. Hold `BOOT`, plug the board in, let go: a drive `RPI-RP2` appears (a board with an empty
   flash shows it without `BOOT`). Copy the `.uf2` onto it; the board restarts as
   MicroPython and the drive goes.
3. Copy the firmware, from the repository's folder:

   ```bash
   uvx mpremote@1.29.0 connect auto cp beam/firmware/core/beamcore.py :beamcore.py + cp beam/firmware/rp2040/main.py :main.py + reset
   ```

   The board's LED turns green, and red while the sensor is covered. The same command
   puts new files on later; MicroPython itself stays.

4. Check it (optional): `uvx mpremote@1.29.0 connect auto repl`, type `HELLO` and Enter
   (what is typed is not shown), cover the sensor; `Ctrl-]` leaves. It says, for example:

   ```text
   HELLO beam-rp2040 0.4 5054316551247c1c 0
   BREAK 1 18734215
   STATUS blocked
   STATUS beam
   ```

`Ctrl-C` in that window stops `main.py`; powering the board off and on starts it again.

## Over Bluetooth

In the chronometer, Device `Beam board RP2040 + BT05 (Bluetooth)`, and the module's name
(`beam-1c1c`, say) in `device`. No pairing is needed: Bluetooth Low Energy connects to the
board by its name. The BT05's own LED blinks while it waits for a reader, and stays lit
once one is connected.
