# Implementation Plan: The boards around, and a clock that knows world time

**Branch**: `003-boards-and-device-time` | **Date**: 2026-11-22 | **Spec**: [spec.md](spec.md)

## Summary

Both apps get one beam source for every board: a list of the boards around, on Bluetooth and USB,
in which the judge picks one or several and presses Blink to tell them apart; every break of every
picked board is a cutoff. And both apps get a device clock: the offset of the device's own clock
from world time, measured from GNSS (the phone) and NTP (both), every cutoff stamped on the
corrected clock, the judge shown its source and how far it may be off. One PR in each repository:
this one, and ChronometerAndroid's.

## Technical Context

**Desktop**: Python 3.14, PySide6, pyserial, bleak (in the connector process only, CLAUDE.md), the
stdlib's `socket` for NTP. **Android**: Kotlin, Compose, the platform's BluetoothLeScanner,
LocationManager and DatagramSocket. **Boards**: unchanged, firmware 0.4. **Testing**: pytest with
the Qt `win` fixture; JUnit with Robolectric.

## Constitution Check

The records stay the source of truth and keep their format (FR-008); a source that does not answer
never holds up timing (FR-015); no new dependency on either side.

## Decisions

1. **One connector for every board picked, `beam-boards`.** A connector process reads several boards
   at once: each picked board is a link of its own, through the USB or Bluetooth link code that
   exists (usb_serial's, ble's, the Bluetooth ones on one asyncio loop), each with its own bridge,
   so its own clock and counts. Every BREAK goes out as it comes: nothing is merged (FR-004). Each
   board's state and errors go to the action log with its name before them (FR-005). Its settings
   are the pick, `{"boards": [{"link": "ble", "device": "<address>", "name": "beam-7c1c"},
   {"link": "usb", "port": "...", "kind": "beam-rp2040"}]}`, and the hold-off; a board on USB
   keeps the kind its USB ids gave, as the two kinds' control lines differ. The four single-board
   entries leave the device list; a pick saved with one of them becomes the same board in
   `beam-boards`. A Bluetooth board's kind is known only from its HELLO, so a bridge takes the
   HELLO of either kind. A board on a cable that also has Bluetooth is found twice; picked on
   both links, it is read on the one that said HELLO first only, and the judge told, or each of
   its breaks would be two cutoffs.
2. **Finding the boards: `beam-scan`.** bleak runs in a connector process only, so a short connector
   fills the list: 5 s of a Bluetooth scan (the name, the address, the signal), the USB ports with
   the boards' ids, one `found` message, and it ends. The window shows them, the picked ones checked,
   those not in reach kept and greyed.
3. **Blink.** Before timing, `beam-blink` opens the one board, sends `FLASH 1` to `FLASH 5` 0.4 s
   apart and ends; while timing, the running `beam-boards` takes a `blink` command for a board it
   holds, as a board takes one reader at a time.
4. **The device list.** The beam source lists Beam boards first, then the test beam and the custom
   command (FR-006).
5. **NTP.** SNTP over UDP to several servers (time.google.com, time.cloudflare.com, pool.ntp.org,
   time.apple.com, time.windows.com), four queries each, the shortest round trip of each kept; a
   server at stratum 0 or 16 or with the alarm set is dropped, then any whose offset is further from
   the others' median than its half round trip (FR-011). The offset is the median of what is left;
   how far it may be off, half the shortest round trip, growing by 50 ppm of the time since it was
   measured, or by 5 ppm once the offset's rate is known from measurements 10 min apart, which the
   clock then follows while the internet is gone. A round at start, then every 64 s, on a thread
   of its own (FR-015).
6. **GNSS, the phone only.** A fix's UTC time against the elapsed-realtime clock at the fix gives an
   offset; it is taken only when two fixes in a row agree within 5 ms (the time moved as the device's
   own clock did) and, when NTP answered within the hour, within 1 s of NTP's (FR-010). Otherwise it
   is dropped and the judge told: a jammed or spoofed GNSS at a start.
7. **The device clock.** `now = the monotonic clock + the offset measured`, or the system's time as
   it is while none is. The first correction is taken at once; after it, a correction that sets
   the clock forward is taken at once, one that would set it back is eased in at a tenth of the
   time running, so the clock never runs backwards (FR-012); one of over a second (a system clock
   set wrong by hand) is taken at once and said, as the cutoffs before it were on the old clock.
   The best source answering wins: GNSS, then NTP, then the system's time as it is (FR-007).
8. **Every stamp on it.** The desktop's hand cutoffs and its clock's display take it; a connector's
   event, timed on the system's clock in its own process, gets the correction as it arrives; the
   phone's taps, sources and repositories take it in place of the system's millis (FR-008).
9. **The judge sees it.** A line under the source: "Clock: GNSS, within 2 ms", "Clock: the
   internet, within 6 ms", "Clock: the system's, not checked"; a change of source, a GNSS time
   dropped and a correction of over a second go to the action log (FR-009).
10. **The phone's permissions.** The location is asked for as timing mode starts (FR-014); the
    foreground service declares the location type, as Android 14 asks of one that reads it.

## Project Structure

Desktop: `app/device_time.py` (NTP and the device clock), `app/connectors/boards/many.py` (the
`beam-boards` connector), `app/connectors/boards/scan.py` (`beam-scan`, `beam-blink`), the source box
in `app/main_window.py`; tests beside the existing ones. Android: `source/board/BoardFinder.kt`, the
`BoardBeamSource` reading several ports, `time/DeviceClock.kt`, `time/Ntp.kt`, `time/GnssTime.kt`,
the source settings' list; tests beside the existing ones.
