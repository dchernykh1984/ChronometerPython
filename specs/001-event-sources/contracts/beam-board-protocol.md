# Contract: the beam board's lines, version 0.5

A beam board (`beam/firmware/`) times each break of its light with its own clock and talks over
a USB serial port, Bluetooth, or both. Every program that reads one keeps to this contract: the
desktop chronometer (`app/connectors/boards/`) and the Android app's beam.

## Boards

| `HELLO` name | Board | USB (vendor:product) | Bluetooth |
| --- | --- | --- | --- |
| `beam-rp2040` | RP2040-Zero, MicroPython | 0x2E8A:0x0005 | a BT05 (an HM-10 clone) on its UART0 |
| `beam-esp32c3` | ESP32-C3 SuperMini, MicroPython | 0x303A:0x1001 | its own |

A board on Bluetooth is advertised as `beam-<id4>`, `<id4>` the last 4 hex digits of its board id:
the ESP32-C3 advertises so, and the RP2040 names its BT05 so at start (a BT05 that does not take
the name keeps its own).

## Transport

- USB CDC serial. The line settings do not matter. On the RP2040 the host sets DTR, or the
  board's output may be dropped. On the ESP32-C3 it sets DTR off and then RTS off, as it opens
  the port: on its own USB, RTS on holds the chip in reset, and DTR on as RTS goes off starts its
  bootloader. One program at a time: the port is opened exclusively where the system allows it,
  as two readers would each get half of every line.
- Bluetooth Low Energy: the serial service 0xFFE0 and its characteristic 0xFFE1, the HM-10's,
  which the ESP32-C3 offers too. The board's characters come as notifications of at most 20 bytes;
  commands go as writes of at most 20 bytes: without response where 0xFFE1 takes them (the
  ESP32-C3), with response where it does not (the prototype's BT05, an MLT-BT05 v6.1, drops any
  other). A program enables the notifications and joins the pieces into lines.
- ASCII lines, each ended by `\r\n` from the board, by `\n` (or `\r`) towards it. The board reads
  at most 64 characters of a line and drops the rest.
- A line is counted only with its line end: one cut short as the link ended may be a `BREAK` with
  half its digits.
- A board with two links answers a command on the link it came from, and says a `BREAK`, a change
  of its `STATUS` and its `HELLO` at start on every link.

## What the board says

`<t_us>` is microseconds since the board started, on its own clock: a whole number that keeps
counting past the 30-bit ticks' wrap.

| Line | When |
| --- | --- |
| `HELLO <name> <firmware> <board id> <seq>` | At start, and when asked `HELLO`. The board id is its chip's unique id in hex, 16 digits on the RP2040 and 12 on the ESP32-C3; `seq` is the count of its last break, 0 before any. |
| `BREAK <seq> <t_us>` | The light went: the time of its first edge. `seq` counts from 1 at each start. Said again, the same, when asked `RESEND`. |
| `STATUS beam`, `STATUS blocked` | The light's state once it has held 50 ms, and when asked `STATUS`. |
| `STATUS unsteady` | No state has held 50 ms for a second: the light flickers on the sensor. |
| `STATUS unknown` | Asked `STATUS` before any state has held. |
| `PONG <n> <got_us> <sent_us>` | Asked `PING <n>`: when the `PING` came, its first character where the link's own transfer time is known (the BT05's UART), its end otherwise; and when this answer went, over the BT05's UART when its first 20 characters had crossed it, as the module sends nothing before. The board waits a random 0 to 49 ms between the two. |
| `HOLDOFF <ms>` | Asked `HOLDOFF <ms>`: the hold-off is now that. |
| `FLASH <n> <t_us>` | Asked `FLASH <n>`: its LED changed for 100 ms, for cameras and for a judge's Blink: lit, or put out where a one-colour LED is lit already (the ESP32-C3's, lit for the light on its sensor). Since 0.5; before, a lit one stayed lit. |
| `ERROR unknown: <line>` | A line it did not understand, the first 40 characters of it. Never on the BT05's UART, where the module's own replies (`OK`, `+NAME=...`) would come back as one. |

Anything else on a link (a MicroPython traceback, the REPL, the BT05's replies) is not the board's
and is ignored.

The board answers `HELLO`, `PING <n>`, `STATUS`, `HOLDOFF <ms>`, `FLASH <n>` and `RESEND <seq>`:
every break it still keeps, its last 128, from count `seq` on, as `BREAK` lines, oldest first.

## When a break is a break

- A break is the first edge of the light going. After it, no edge is a break until both the
  hold-off has passed (1000 ms unless told otherwise: a bike's wheels and its rider are one break)
  and the light has been back for at least 50 ms. Light coming back after a long block, or onto a
  laser being aimed, chatters, and that is no break.
- At start no edge is a break until the light has held for 50 ms.
- A light that never holds (`STATUS unsteady`) gives no break at all: the program says so.

## What a reading program does

1. Opens the link and sends `\n` (to end any half line), `HOLDOFF <ms>`, `HELLO`, `STATUS`. Over
   USB it takes the port it was told, else the first with the board's ids; over Bluetooth only the
   board it was told, by name or address, never another one in range. Told none, it says the
   boards it finds and reads none.
2. Takes the board only from a `HELLO` with the board's name; until then no line counts. A `BREAK`
   that comes before it, or before the board's clock is read (step 4), is a rider all the same,
   and waits: once both are known, it is timed by the board's clock. Given up on 3 s after it came
   (10 s over Bluetooth, where the clock takes 4 answers), it takes the time its line came, and that
   is said. A `HELLO` with another firmware version than the one the program was built for is said
   as an error; its breaks still count.
3. Catches up after the `HELLO`, and asks `HELLO` again every 5 s for the board's count. The first
   `HELLO` from a board id gives the count the program starts from: breaks before it were not its
   own. A later one, after the link came back or asked again: a `seq` above the last count taken
   asks `RESEND <last + 1>` (a break whose line was lost on the way, the last of a race say, that no
   later break would show); a `seq` below it means the board started again, and asks `RESEND 1` when
   it is above 0. A `HELLO` asked again is said to the judge only when it says something new.
4. Sends `PING <n>` every 2 s over USB and every 0.5 s over Bluetooth, `n` never used before by this
   program. A `PONG <n> <got_us> <sent_us>` received at `got`, its `PING` sent at `sent`, both on
   the program's clock, gives the way there `a = got_us / 1000 - sent` and the way back
   `b = got - sent_us / 1000`; the offset, the program's clock less the board's, is `(b - a) / 2`.
   - Over USB, the round trip less the board's wait, `a + b`, must be at most 20 ms; the median of
     the last 9 offsets maps a break's `t_us` onto the program's clock. An offset more than 50 ms
     from that median means the program's clock was set anew: the offsets before it no longer
     count.
   - Over Bluetooth, a trip waits for the radio's next connection event, so the offset is
     `(min b - min a) / 2` over the last 32 `PONG`s, read once 4 have come. A `PONG` whose own
     `(b - a) / 2` is more than 100 ms from the offset means the clock was set anew: it starts
     again.
   A line is timed when its first piece came, over USB as over Bluetooth: timed at its end, it
   would carry the time its last characters took to come.
   When the link is opened again, the board may have started again: no earlier offset counts.
5. Takes each count once: a `BREAK` whose `seq` was taken from that board id already is dropped. A
   `seq` that skips some asks `RESEND <first missing>`; counts still missing 10 s later are said:
   their breaks never came. A `seq` below the last, not one asked for, is the board started again.
6. Says, once each and only when it changes, in the place the judge reads:
   - no board found, or the link could not be opened, with the reason;
   - a `PING` unanswered for 6 s: the board's program has stopped, though its link is up;
   - `STATUS blocked` or `STATUS unsteady` held for over 2 s, longer than any rider takes: no break
     can be seen; and the light back;
   - breaks that never came (step 5).
7. Tries the link again every 2 s while it is gone.
