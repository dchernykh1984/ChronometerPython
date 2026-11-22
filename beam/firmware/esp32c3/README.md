# The ESP32-C3 SuperMini beam board

The ESP32-C3 SuperMini times the beam's breaks. It reports them over its USB cable, and
over its own Bluetooth: no module to add. [`../../README.md`](../../README.md) has the
kits, the chronometers' settings and what their log says.

## Parts

| Part | Notes |
| --- | --- |
| ESP32-C3 SuperMini | USB-C, a blue LED on GPIO8, `BOOT` and `RST` buttons. Its pins usually come apart, to be soldered. |
| Light sensor module | LM393 comparator, a photoresistor and a trimmer; pins VCC, GND, DO, AO. |
| KY-008 laser module | 650 nm, 5 V, on the other side of the course, on its own power. |
| Dupont wires, female-female | 3 for the sensor, 2 for the laser while trying it on the table. |

## Wiring

Hold the board with the chip facing you and the USB socket up. One row reads, from the
USB end, `5V`, `G`, `3.3`, `4`, `3`, `2`, `1`, `0`; the other `5`, `6`, `7`, `8`, `9`, `10`,
`20`, `21`.

| Module pin | Board pin | Why |
| --- | --- | --- |
| Sensor `VCC` | `3.3` | Not 5V: `DO` swings up to `VCC`, and a GPIO takes 3.3 V at most. |
| Sensor `GND` | `G` | |
| Sensor `DO` | `3` (GPIO3) | High while the light is gone. Pulled up on the board: a loose wire reads as a blocked beam. GPIO2, 8 and 9 are strapping pins: a sensor there could hold the chip in its bootloader at power-up. |
| Sensor `AO` | - | Not used. |
| Laser `S` | `5V` | On the table only: at a race the laser has its own power bank. |
| Laser `-` | `G` | The board has one `G` pin: share it with a Y wire. |

The blue LED is lit while the light reaches the sensor, for aiming, and for `FLASH`.

## Flashing

1. Download MicroPython and check it:

   ```bash
   curl -LO https://micropython.org/resources/firmware/ESP32_GENERIC_C3-20260824-v1.29.0.bin
   shasum -a 256 ESP32_GENERIC_C3-20260824-v1.29.0.bin
   # bf72ed9eb88ad3a8f49d02c3d371f9ea34c90a8a303aeb9e324d8efd4a2a655a
   ```

2. Plug the board in and put MicroPython on it. If esptool finds no board, hold `BOOT`,
   press and let go `RST`, then let go `BOOT`, and try again:

   ```bash
   uvx esptool@5.6.0 --chip esp32c3 erase-flash
   uvx esptool@5.6.0 --chip esp32c3 write-flash 0 ESP32_GENERIC_C3-20260824-v1.29.0.bin
   ```

   Press `RST` afterwards.
3. Copy the firmware, from the repository's folder:

   ```bash
   uvx mpremote@1.29.0 connect auto cp beam/firmware/core/beamcore.py :beamcore.py + cp beam/firmware/esp32c3/main.py :main.py + reset
   ```

   The blue LED lights while light reaches the sensor and goes out when it is covered.
   The same command puts new files on later; MicroPython itself stays.

4. Check it (optional): `uvx mpremote@1.29.0 connect auto repl`, type `HELLO` and Enter,
   cover the sensor; `Ctrl-]` leaves. It says, for example:

   ```text
   HELLO beam-esp32c3 0.5 a0b1c2d34e5f 0
   BREAK 1 18734215
   STATUS blocked
   STATUS beam
   ```

5. Check its clock: every board, each time it is flashed. Close the chronometer (and the
   REPL), then from the repository's folder:

   ```bash
   uv run python -m beam.tools.clock_check
   ```

   For 5 minutes it PINGs the board over USB and over its own Bluetooth, as `beam-` and
   the last 4 hex digits of its id. It ends `result: every check within`; a line `OUTSIDE`
   is a board to look at before it times a race ([Accuracy](../../README.md#accuracy)).

## Over USB

In the chronometer: Device `Beam board ESP32-C3 (USB)`. Both apps open its port with DTR
and RTS off, DTR first: on the chip's own USB, RTS holds it in reset, and DTR as RTS goes off
starts its bootloader. On macOS and Linux, opening a port may still raise both for a moment
and restart the board once: its count then starts again, which the chronometer handles. That
is to be checked on the board (spec 002, task T015).

## Over Bluetooth

The board advertises itself as `beam-` and the last 4 hex digits of its board id
(`beam-4e5f` for the one above). In the chronometer: Device
`Beam board ESP32-C3 (Bluetooth)`, and that name in `device`. No pairing is needed.

Its Bluetooth offers the same serial service as the RP2040's BT05 (0xFFE0, characteristic
0xFFE1), so both boards are read the same way.
