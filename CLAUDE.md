# Chronometer - project guide for Claude

Offline race timing for a finish judge: a PySide6 desktop app that stamps finish
and lap crossings, writes them to plain text files next to the executable, and
pushes them to the cycling site over HTTP. The files are the source of truth;
the network is best effort.

## Layout

| Path | What lives there |
| --- | --- |
| `app/main.py` | Entry point (`uv run python -m app.main`). |
| `app/main_window.py` | The whole Qt UI and every event handler. |
| `app/models.py` | Pure logic: time formatting, file I/O, config parsing. No Qt. |
| `app/http_io.py` | The site API client (stdlib `urllib`, 10s timeouts). |
| `app/paths.py` | Resolves where data lives (see below). |
| `tests/` | pytest; `conftest.py` holds the offscreen Qt `win` fixture. |
| `data/` | Runtime data files. |
| `beam/` | Everything for the laser beam: `README.md` (the kits, parts and prices, wiring, flashing, both apps), `firmware/` (one core, `core/beamcore.py`, and a `main.py` per chip, `rp2040/` and `esp32c3/`), `enclosures/` (the 3D-printed parts, made in Blender), `tools/` (`clock_check.py`, the clock check every board gets when flashed). The firmware's tests (`tests/test_beam_firmware.py`) run with the rest, outside the coverage gate, which measures `app/` only. |
| `app/connectors/boards/` | The beam boards the chronometer reads itself: the contract's reader (`protocol.py`), the USB transport (`usb_serial.py`), the Bluetooth one (`ble.py`, through `bleak`), one module per chip (`rp2040.py`, `esp32c3.py`), each a USB device and a Bluetooth one. |

`app/models.py` is a port of an older C++ chronometer; several helpers say so in
their docstrings. Keep the ported behaviour unless a change is asked for.

## Where the app keeps its data

`app/paths.py:base_dir()` returns the folder that contains the runnable when
frozen (PyInstaller; on macOS the folder containing the `.app` bundle) and the
current working directory in development. Every data file is resolved against
it, so one copied folder per event keeps its own settings, results and counters.

- `data/groupsList.txt` - group list plus the two file paths, positional format.
- `data/http_config.txt` - site upload settings, `key=value`. Holds the
  competition token: never commit it, never paste its contents anywhere.
- results / groups files - paths chosen in the UI, one line per record,
  `number#time#action#` and `group#time#`.
- `temp/stc<timestamp>[_nn].txt` - backups of the action log and the slots:
  after every hand action, DSQ and correction, before Empty all, and within
  2 s of beam breaks or chip crossings, unless backup is disabled.

## Site upload (three streams, one snapshot each)

Uploads only run when `site_url`, `token` and `device_id` are all set;
otherwise they are skipped silently. Each upload posts the *whole* file, keyed
by `device_id`, with an incrementing `client_revision` the server uses to reject
a stale overwrite (HTTP 409).

| Trigger | Endpoint |
| --- | --- |
| A record is written to the results file (`_write_to_finish`), 400ms debounce | `/api/v1/finish-times/` when point number is 0, else `/api/v1/remote-points/` |
| "Save group" | `/api/v1/group-times/` |
| "Get groups" (read) | `/api/v1/participants/` |

Uploads run on a `QThread` so a slow network never blocks timing, and their
outcome is appended to the in-app action log, not shown in a dialog. See the
`diagnose-site-upload` skill for the failure modes.

## The beam

- The boards' lines are a contract:
  `specs/001-event-sources/contracts/beam-board-protocol.md`. Change it first, then the
  firmware, this chronometer (`app/connectors/boards/protocol.py`) and the Android app
  (ChronometerAndroid's `BoardBridge.kt`) together, and bump `FIRMWARE` in
  `beam/firmware/core/beamcore.py` and the version the readers expect
  (`app/connectors/boards/rp2040.py`, and Android's), or every board is said to need
  flashing.
- MicroPython runs `beam/firmware/`: no syntax newer than Python 3.8, no `pathlib`, no
  typing at run time. `beam/ruff.toml` keeps the formatter's 3.14 style out (an
  `except A, B:` without parentheses stops a board at its start); a test parses every
  file as 3.8.
- Over Bluetooth both boards offer the HM-10's serial service, 0xFFE0 with 0xFFE1, and a
  reader reads only the board its `device` setting names. The clock is mapped from the
  shortest trip each way of the last 16 PONGs (`RadioSync`), never from a round trip's
  middle: a radio reply waits for its next connection event.
- The prototype's hardware has quirks the code keeps to, each in a test: its BT05 (an
  MLT-BT05 v6.1) takes writes with response only (a reader picks the write from 0xFFE1's
  properties), counts its bauds from 1200 (8 is 115200) and answers nothing for about 2 s
  after a new name; the ESP32-C3's MicroPython has no hard pin IRQ (a scheduled one, up to
  1.2 ms late in a garbage collection).
- The clock is mapped anew at every PONG, never once at the connection and kept
  (spec 002, FR-022, the owner's choice). `beam/tools/clock_check.py` measures what it
  rests on, on every board flashed; a change to the mapping is checked with it.
- `bleak` runs in the connector process, never in the UI's. Its backend for each system is
  collected in `.github/workflows/build.yml`. The macOS bundle needs
  `NSBluetoothAlwaysUsageDescription`, or macOS ends the app at its first Bluetooth call.
  `.github/scripts/connector_smoke.py` runs a Bluetooth connector in every frozen build.
- The enclosures are made by `beam/enclosures/beam_enclosures.py` in Blender. Change
  the script, never an STL, and build them again. Use Blender's MCP add-on (Blender Lab's,
  `localhost:9876`: a JSON request `{"type": "execute", "code": ..., "strict_json":
  false}` ended by a NUL byte, with `__file__` set in the code), its Text Editor, or
  `blender -b -P`. Commit the script, `stl/`, `preview.png` and the `.blend` together.

## Commands

```bash
uv sync                                  # install
uv run python -m app.main                # run the app (never python app/main.py)
uv run pytest                            # tests, -n auto, coverage gate 90%
uv run pre-commit run --all-files        # everything CI's pre-commit job runs
```

`uv sync` installs the dev group by default (`tool.uv.default-groups = "all"`).
Python is pinned to 3.14.

## Conventions

- **ASCII only.** A pre-commit hook rejects non-ASCII in `.py`, `.md`, `.yml`,
  `.toml`, `.json` and shell files (`CHANGELOG.md` and `uv.lock` are exempt).
  No typographic dashes, no quotes-as-glyphs, no Cyrillic in files. Spec Kit's
  generated files (`.specify/` but the constitution, the `speckit-*` skills) are
  out of every hook: `specify` keeps a file it finds edited instead of updating it.
- **LF line endings** everywhere, enforced by `.gitattributes` and pre-commit.
- **ruff** with a broad rule set (line length 88, bugbear, bandit, pathlib,
  pyupgrade, mccabe max-complexity 10) and **mypy**. Run them via pre-commit.
- **Conventional commits, one line, no body, no trailers.** `cz check` runs on
  every PR. Never add a `Co-Authored-By` line or Claude attribution to a commit
  or a PR body.
- **Coverage gate is 90%**, with `app/main.py` and `app/main_window.py` omitted
  from the measurement. UI handlers are still covered by Qt-level tests through
  the `win` fixture - add one there when you touch a handler.
- **Stay in scope.** This app writes race results that cannot be re-recorded.
  When the task is tooling or config, do not touch `app/` or `tests/`. If you
  spot an unrelated problem, report it and let the user decide.

## Release

release-please owns versioning: merging conventional commits to `main` opens a
release PR, and merging that cuts the tag, builds the portable apps for every
platform and attaches them to the GitHub release. Do not bump the version in
`pyproject.toml` by hand.
