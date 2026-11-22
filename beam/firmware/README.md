# The beam boards' firmware

Every board runs one core, and its chip's `main.py` wires that core to the chip.

| File | What it is | On the board as |
| --- | --- | --- |
| [`core/beamcore.py`](core/beamcore.py) | Breaks, the light's state, the commands, the links: the same on every chip. | `beamcore.py` |
| [`rp2040/main.py`](rp2040/main.py) | The RP2040-Zero: its pins, its colour LED, USB, and a BT05 on UART0. | `main.py` |
| [`esp32c3/main.py`](esp32c3/main.py) | The ESP32-C3 SuperMini: its pins, its LED, USB, and its own Bluetooth. | `main.py` |

The two files copied onto a board are exactly these. What a board says and answers is
the contract
[`specs/001-event-sources/contracts/beam-board-protocol.md`](../../specs/001-event-sources/contracts/beam-board-protocol.md).
The firmware's version is `FIRMWARE` in `core/beamcore.py`. A board says it in its
`HELLO`, both chronometers read the same version, and a test keeps them equal.

## Versions

| What | Version | Pinned in |
| --- | --- | --- |
| MicroPython for the RP2040-Zero | v1.29.0, build `RPI_PICO` | [`rp2040/README.md`](rp2040/README.md), with its SHA-256 |
| MicroPython for the ESP32-C3 | v1.29.0, build `ESP32_GENERIC_C3` | [`esp32c3/README.md`](esp32c3/README.md), with its SHA-256 |
| mpremote (copies files to a board) | 1.29.0 | the chips' commands |
| esptool (puts MicroPython on the ESP32-C3) | 5.6.0 | the ESP32-C3's commands |
| The firmware | 0.5 | `FIRMWARE` in `core/beamcore.py` |

## How the core works

- **Breaks.** The sensor's pin raises an IRQ on the light's first edge: a hard one on the
  RP2040, a scheduled one on the ESP32-C3, whose MicroPython has no other (tens of
  microseconds later, up to 1.2 ms in a garbage collection). The IRQ keeps the moment,
  and takes no other edge until the loop arms it again: once the hold-off has passed and
  the light has held for 50 ms. A comparator's chatter in the half-light can never pile
  up breaks or move their time.
- **Links.** A board has one or two links, USB and Bluetooth. An answer goes back on the
  link its command came from; a break, a change of the light and the start's `HELLO` go
  on every link.
- **PONG.** It gives both of the board's moments, when the `PING` came and when the answer
  went. The board waits a random 0 to 49 ms between them, so that over Bluetooth some
  answers fall right before a radio event: the reader takes the shortest trip each way.
  Over the BT05's UART both moments count the characters' own time: the `PING`'s first
  one, and the answer's first 20, which the module holds before it sends them.
- **RESEND.** The board keeps its last 128 breaks and says them again when asked, a line
  at a time once the link has sent the last: 128 of them at 9600 baud would hold the loop,
  and with it the next break, for 3 s. A link that came back is so caught up, the breaks
  with their own times; the readers ask the board's count every 5 s too, so a last break
  whose line was lost on the way comes all the same.

## Tests

`tests/test_beam_firmware.py` runs the core and both mains on the computer, with
MicroPython's modules faked, as part of `uv run pytest`. A test also parses every file
here as Python 3.8: MicroPython knows no newer syntax. `beam/ruff.toml` keeps the
formatter from writing any.
