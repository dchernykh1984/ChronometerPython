# Contract: the connector protocol, version 1

A connector is a program that talks to one timing device -- a chip reader or a light beam -- and
reports what the device sees to a chronometer. ChronometerPython runs each connector as a child
process; ChronometerAndroid runs its sources inside the app and reports the same events. A device
that can speak this protocol itself (a future USB or Bluetooth beam) is a connector of its own.

## Transport

- The chronometer starts the connector and writes **commands** to its standard input; the
  connector writes **events** to its standard output.
- Both directions carry UTF-8 JSON objects, one per line, ended by `\n`. A line longer than
  65536 bytes is an error and is dropped.
- Standard error is free text; the chronometer may show it in its log.
- Unknown fields are ignored on both sides. An unknown `type` or `cmd` is logged once and ignored.
  A line that is not a JSON object is logged and ignored.
- The connector exits when its standard input ends: the chronometer is gone.

## Lifecycle

1. The chronometer starts the program: a built-in connector as `<chronometer> --connector <name>`,
   any other as the command line the judge entered.
2. Within 30 s the connector writes `hello`; a onefile build unpacks itself before it starts, which
   antivirus scanning on a slow laptop can stretch past 10 s. Without it the start failed, and the
   connector is started again as in step 6. A `hello` with another `protocol`, or of another
   `kind` than the source, makes the chronometer stop it for good and report why: such a program
   would only fail again.
3. The chronometer sends `start` with the connector's settings; the connector begins to report.
4. Every 5 s the chronometer sends `ping`; the connector answers `pong` with the same `id`. With
   no `pong` for 15 s the chronometer kills and restarts the connector.
5. To stop, the chronometer sends `stop` and closes standard input; a connector still running 3 s
   later is killed.
6. A connector that exits, fails to start, sends a `fatal` error or misses its pings is started
   again after 1 s, the pause doubling up to 30 s while it keeps failing and returning to 1 s after
   30 s of running without a failure.

## Commands (chronometer to connector)

| `cmd` | Fields | Meaning |
| --- | --- | --- |
| `start` | `settings`: object | Begin reporting, with the settings the judge chose for this connector. |
| `stop` | | Stop reporting; exit soon. |
| `ping` | `id`: integer | Answer with `pong`. |

## Events (connector to chronometer)

| `type` | Fields | Meaning |
| --- | --- | --- |
| `hello` | `protocol`: 1; `connector`: string; `kind`: `"chips"` or `"beam"` | First line after start. |
| `read` | `chip`: string; optional `time_ms`, `device_time`, `antenna`, `rssi`, `reader` | One chip read. |
| `beam` | `seq`: integer; optional `time_ms`, `device_time` | One break of the beam. |
| `status` | `state`: `"connecting"`, `"connected"` or `"disconnected"`; optional `detail` | The device link changed. |
| `error` | `message`: string; optional `fatal`: boolean | Something went wrong; `fatal` means the connector cannot go on. |
| `pong` | `id`: integer | Answer to `ping`. |

Field rules:

- `chip`: the id as the device reports it; the chronometer normalises it (upper case, ASCII letters
  and digits only) before looking it up. An empty id after normalisation makes the read invalid.
- `time_ms`: Unix time in milliseconds **on the chronometer's clock** -- the connector maps a
  device clock to it when it can. Without `time_ms` the chronometer uses the time it received the
  event.
- `device_time`: the device's own time, as text, exactly as reported; kept for later analysis.
- `antenna`: text (port number or name). `rssi`: number, dBm. `reader`: text (address or serial).
- `seq`: the beam's own break counter when it has one, else the connector's count from 1.

## Examples

```text
> {"type":"hello","protocol":1,"connector":"dummy-chips","kind":"chips"}
< {"cmd":"start","settings":{"chips":["A1","B2"],"period_s":3}}
> {"type":"status","state":"connected"}
> {"type":"read","chip":"a1","time_ms":1761725400123,"antenna":"1","rssi":-58.5,"reader":"dummy"}
< {"cmd":"ping","id":7}
> {"type":"pong","id":7}
> {"type":"beam","seq":12,"time_ms":1761725401500,"device_time":"812345"}
< {"cmd":"stop"}
```

## Devices the protocol must cover

- LLRP readers (Impinj, Zebra): EPC, antenna port, peak RSSI, first-seen timestamp in
  microseconds of the reader clock (`device_time`), reader address.
- The RaceResult decoder: transponder code, its time, the loop/antenna id, hit count and strength.
- Cheap R2000 modules with their own serial or TCP framing: EPC, antenna, RSSI; no clock, so
  `time_ms` is the receipt time.
- A light beam over USB serial or Bluetooth LE: a break counter and a device tick.
