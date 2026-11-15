# Contract: the beam board's lines, version 0.3

The beam board (`firmware/beam_rp2040/main.py`) times each break of its light with its own
clock and talks over its USB serial port. Every program that reads it keeps to this contract:
the desktop connector (`firmware/beam_rp2040/connector.py`) and the Android app's USB beam.

## Transport

- USB CDC serial: vendor 0x2E8A, product 0x0005 (MicroPython on an RP2040). The line settings
  do not matter; the host sets DTR, or the board's output may be dropped.
- ASCII lines, each ended by `\r\n` from the board, by `\n` (or `\r`) towards it. The board
  reads at most 64 characters of a line and drops the rest.
- One program at a time: the port is opened exclusively where the system allows it, as two
  readers would each get half of every line.
- A line is counted only with its line end: one cut short as the port ended may be a `BREAK`
  with half its digits.

## What the board says

`<t_us>` is microseconds since the board started, on its own clock: a whole number that keeps
counting past the 30-bit ticks' wrap.

| Line | When |
| --- | --- |
| `HELLO beam-rp2040 <firmware> <board id>` | At start, and when asked `HELLO`. The board id is 16 hex digits. |
| `BREAK <seq> <t_us>` | The light went: the time of its first edge. `seq` counts from 1 at each start. |
| `STATUS beam`, `STATUS blocked` | The light's state once it has held 50 ms, and when asked `STATUS`. |
| `STATUS unsteady` | No state has held 50 ms for a second: the light flickers on the sensor. |
| `STATUS unknown` | Asked `STATUS` before any state has held. |
| `PONG <n> <t_us>` | Asked `PING <n>`. |
| `HOLDOFF <ms>` | Asked `HOLDOFF <ms>`: the hold-off is now that. |
| `FLASH <n> <t_us>` | Asked `FLASH <n>`: its LED lit white for 100 ms, for cameras. |
| `ERROR unknown: <line>` | A line it did not understand, the first 40 characters of it. |

Anything else on the port (a MicroPython traceback, the REPL) is not the board's and is ignored.

## When a break is a break

- A break is the first edge of the light going. After it, no edge is a break until both the
  hold-off has passed (1000 ms unless told otherwise: a bike's wheels and its rider are one break)
  and the light has been back for at least 50 ms. Light coming back after a long block, or onto a
  laser being aimed, chatters, and that is no break.
- At start no edge is a break until the light has held for 50 ms.
- A light that never holds (`STATUS unsteady`) gives no break at all: the program says so.

## What a reading program does

1. Opens the port and sends `\n` (to end any half line), `HOLDOFF <ms>`, `HELLO`, `STATUS`.
2. Takes the board for this firmware's only from the `HELLO` it asked for, with the name
   `beam-rp2040`; until then no line counts. A `BREAK` that comes before it (in the milliseconds
   the board takes to read the `HELLO`) or before the board's clock is read (step 3) is a rider all
   the same, and waits: once both are known, it is timed by the board's clock. That is right even
   for a line the system kept from before the port was opened. Given up on 3 s after it came, it
   takes the time its line came, and that is said. A board that never says the `HELLO` has none of
   its lines counted. A `HELLO` with another firmware version than the one the program was built
   for is said as an error; its breaks still count.
3. Sends `PING <n>` every 2 s, `n` never used before by this program. A `PONG <n>` received
   `got` ms after its `PING` was sent at `sent`, both on the program's clock, gives the offset
   `(sent + got) / 2 - t_us / 1000`, unless the round trip `got - sent` is over 20 ms. The median
   of the last 9 offsets maps a break's `t_us` onto the program's clock; a break before any offset
   waits for one (step 2). An offset more than 50 ms from that median means the program's
   clock was set anew (round trips this short agree within 10 ms): the offsets before it no longer
   count. When the port is opened again, the board may have started again:
   no earlier offset counts.
4. Says, once each and only when it changes, in the place the judge reads:
   - no board found, or the port could not be opened, with the reason;
   - a `PING` unanswered for 6 s: the board's program has stopped, though its port is open;
   - `STATUS blocked` or `STATUS unsteady` held for over 2 s, longer than any rider takes: no break
     can be seen; and the light back;
   - a `BREAK` whose `seq` skips some after the last one from the same board id: those breaks never
     came, the link down as they did; a `seq` lower than the last is the board started again.
5. Tries the port again every 2 s while it is gone.
