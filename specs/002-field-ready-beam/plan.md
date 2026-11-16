# Implementation Plan: A beam ready for real races

**Branch**: `002-field-ready-beam` | **Date**: 2026-11-16 | **Spec**: [spec.md](spec.md)

## Summary

Two kits, both on Bluetooth: an RP2040-Zero with a BT05 (an HM-10 clone) on its UART, and an
ESP32-C3 SuperMini with Bluetooth on its own chip. One MicroPython core times the breaks on every
board; each board's `main.py` only wires it to its pins and links. The contract goes to version
0.4: a Bluetooth transport, a PONG that carries both of the board's moments, and RESEND for breaks
a dropped link missed. The desktop chronometer reads the boards over Bluetooth through `bleak`, the
Android app through its own Bluetooth stack (a pull request of its own). The first enclosures are
made in Blender, through its MCP bridge, for a 60 mm lens.

## Technical Context

**Language/Version**: MicroPython 1.29 on the boards; Python 3.14 (desktop); Kotlin (Android)
**Primary Dependencies**: `bleak` for Bluetooth Low Energy on the desktop (Windows, macOS, Linux);
`pyserial` as today; Android's `BluetoothGatt`; Blender 5.2 for the models
**Testing**: pytest (the firmware run on the computer with MicroPython's modules faked, the
connectors with a fake link); JUnit and Robolectric on Android
**Target Platform**: RP2040-Zero, ESP32-C3 SuperMini; the desktop's portable builds; Android 7+
**Constraints**: a break is timed on the board (FR-001); the clock mapping within 2 ms over
Bluetooth (FR-002); a beam's optics at most 10,000 tenge (FR-020)

## Constitution Check

- I-II: a break is never lost: the board keeps its last 128 breaks and says them again on RESEND;
  a host asks after every reconnection and after any gap in the counts.
- III: the Bluetooth link lives in the connector process, never in the chronometer's UI thread.
- V: the contract is changed first (0.4), for both apps and every board; the firmware version
  check makes a board and an app on different versions say so.
- VII: every new path has a test; the hardware-only parts (the radio, the BT05's AT commands) are
  marked for the field test.

## Project Structure

```text
beam/                         everything for the beam (FR-017)
  README.md                   the kits: parts and prices, wiring, flashing, the apps, trouble
  firmware/
    core/beam.py              the board logic every chip runs: breaks, light, commands, links
    rp2040/main.py, README.md the RP2040-Zero: USB, and the BT05 on UART0 (GP0, GP1)
    esp32c3/main.py, README.md the ESP32-C3 SuperMini: USB, and Bluetooth of its own
  enclosures/
    README.md                 print settings, assembly, the lens
    beam_enclosures.py        the Blender script that builds every part
    beam_enclosures.blend     the parts as Blender keeps them
    stl/                      one print file per part
app/connectors/boards/        rp2040.py, esp32c3.py; protocol.py; usb_serial.py; ble.py
```

## Decisions

1. **One core, a main per chip.** The break logic is the same on every chip; only pins, the LED and
   the links differ. Flashing copies `core/beam.py` and the chip's `main.py`.
2. **Answers to the asker, news to all.** A board may have two links (USB and Bluetooth). A PONG,
   HOLDOFF, FLASH, ERROR or a HELLO asked for goes back on the link that asked; a BREAK, a change
   of STATUS and the HELLO at start go to every link.
3. **One Bluetooth profile.** Both boards offer the HM-10's serial service, 0xFFE0 with the
   characteristic 0xFFE1 (notify, and write without response): the BT05 has it, the ESP32-C3's
   firmware offers the same, so each app has one Bluetooth path. Lines travel in pieces of at most
   20 bytes; the app joins them.
4. **The clock over Bluetooth.** A round trip there is 15 to 60 ms and lopsided: a reply waits for
   the radio's next connection event. So `PONG <n> <got_us> <sent_us>` gives both of the board's
   moments, the board waits a random 0-49 ms before it answers, so that its answers fall anywhere
   between connection events, and the app keeps, for each way, the shortest trip of its last 16:
   the offset is half the difference of the two. Over USB the median of 9 offsets stays, each now
   leaving out the board's own wait.
5. **A line's moment.** Over USB a line is timed when its end comes; over Bluetooth when its first
   piece does. On the BT05's UART the board subtracts the line's own transfer time, as the
   characters take about 1 ms each at 9600 baud.
6. **The BT05 set up by the board.** At start, while nothing is connected to it, the RP2040 names
   the BT05 `beam-<last 4 hex digits of its id>` and asks it for 115200 baud, checking each answer;
   whatever fails, it keeps 9600 and goes on. Lines from the BT05 that are not commands get no
   ERROR back, so its own answers never echo between the two.
7. **RESEND.** The board keeps its last 128 breaks and says them again a line a turn. An app
   asks `HELLO` every 5 s, whose count shows a break it missed, the last of a race say, and
   sends `RESEND <seq>` after any HELLO whose count is ahead of what it took, and on any gap;
   it takes a count it has already had only once, and says a gap not filled within 10 s. A
   HELLO whose count went down is the board started again: its clock is read anew.
8. **Picking a board.** The ESP32-C3 advertises `beam-<4 hex>`, the RP2040 renames its BT05 the
   same way. The app is told a board's name or address (`device` in its settings) and reads no
   other; with none told, it lists the boards it finds and connects to none (FR-007).
9. **Not yet.** The power level (FR-008) waits for the power choice (a power bank cannot be read);
   FLASH on the ESP32-C3 lights its small LED, which no camera sees at 10 m: an external LED comes
   with the enclosures. Both are listed in tasks.md.
10. **The lens.** The first receiver is made for a 60 mm lens of about 100 mm focal length (a 3x
    hand magnifier's): FR-009's 2 cm of wavering at 10 m leaves the spot on it with room to spare.
    The sensor slides in its tube to find the focus; another lens changes two numbers in the
    Blender script.
11. **A clock read all the time, checked on every board.** The mapping is read anew at every
    answer, never once at the connection (FR-022): set once, its own error would stay for the
    race and the crystal's 10 to 30 ppm (36 to 108 ms an hour) would pile on it; read all the
    time, the drift counts only over its last answers, 18 s at most, 0.5 ms at 30 ppm. Whether
    that holds is measured on every board flashed by `beam/tools/clock_check.py`: it PINGs the
    board over USB and Bluetooth at once at the chronometer's pace, maps its clock as the
    chronometer does, and says each hypothesis within or OUTSIDE. Half a USB round trip bounds
    the cable's mapping; over Bluetooth no trip does, so the cable's mapping at the same
    moments is the reference, and a lopsided way through the radio shows against it.
