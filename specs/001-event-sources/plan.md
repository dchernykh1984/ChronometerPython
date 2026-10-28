# Implementation Plan: Event sources -- by hand, light beam and timing chips

**Branch**: `feat/event-sources` | **Date**: 2026-10-29 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-event-sources/spec.md`

## Summary

The judge picks an event source: by hand (always on), a light beam or chips. Beam and chips run a
connector -- a child process speaking the [connector protocol](contracts/connector-protocol.md) --
that the window starts, watches and restarts. Chip reads go to a raw file first, then through a
chip map built from the start protocol file and a pass tracker that applies the dead time, and
become ordinary crossings in the results file. Beam breaks stamp the slots like the second-user
button. A "Crossings" tab lists the results file and lets the judge add, edit and delete crossings,
each change backed up and written atomically. A button downloads the start protocol from the site.
Test connectors (dummy chips, dummy beam, replay) make all of it work without hardware; the real
readers are stubs.

## Technical Context

**Language/Version**: Python 3.14

**Primary Dependencies**: PySide6 (`QProcess`, `QThread`); standard library only otherwise

**Storage**: plain files next to the results file and in `data/` and `temp/` (see
[data-model.md](data-model.md) and [contracts/raw-files.md](contracts/raw-files.md))

**Testing**: pytest (`-n auto`), offscreen Qt `win` fixture, real child processes for connector
tests; coverage gate 90% without `app/main.py` and `app/main_window.py`

**Target Platform**: portable builds for Windows (onefile, windowed), macOS Apple Silicon (.app)
and Linux (onefile)

**Project Type**: desktop application

**Performance Goals**: 1000 reads per second handled without a visible stall of the window; a
crossing written within 100 ms of the read that makes it

**Constraints**: constitution II-IV: a crossing is on disk before anything else; nothing blocks the
window; nothing is downloaded on its own

**Scale/Scope**: up to about 1000 bibs, 3 chips each, a few readers; a race of up to 12 hours

## Constitution Check

| Principle | How the plan meets it |
| --- | --- |
| I. Crossings only | Chips and beam make `number#time#action#` lines; laps stay with FinishProtocolGenerator. The crossing counts next to the slots stay a hint. |
| II. A crossing is never lost | A read is in the raw file before it is processed; a crossing is appended before the chip state records it (research 4, known limit: a crash in between can repeat one crossing, never lose one). Edits back up first and are refused without a backup. |
| III. The judge is never blocked | Connectors are processes; their output is read asynchronously; downloads run on the worker thread; reads are processed in batches per output chunk. |
| IV. Files are the source of truth | Raw files, the chip state and the start protocol file are the record; the download happens only on the button; uploads stay snapshots. |
| V. Formats are a shared contract | Results lines unchanged; field 11 read by index; raw files and the protocol documented in `contracts/` for ChronometerAndroid. |
| VI. One folder per event | `data/sources.txt`, `data/start.txt` and the files next to the results file resolve through `app_path`. |
| VII. Tests | Pure modules for the protocol, chips, results rewrite and report; Qt-level tests for every handler; shared vectors in `contracts/chip-pass-vectors.json`. |
| VIII. Plain history | One commit per task below. |

No violation. One deliberate behaviour change of hand mode: crossing counts follow the results file
instead of the action log (research 8); the spec's SC-004 and `specs/app/chronometer.md` are updated
to say so.

## Project Structure

### Documentation (this feature)

```text
specs/001-event-sources/
  spec.md
  plan.md                         this file
  research.md                     decisions and their reasons
  data-model.md                   settings, passes, state and backups
  quickstart.md                   trying it out with the test connectors
  contracts/
    connector-protocol.md         shared with ChronometerAndroid
    raw-files.md                  chip reads and beam breaks files
    chip-pass-vectors.json        shared test cases for the pass rule
  tasks.md                        ordered tasks, one commit each
```

### Source Code (repository root)

```text
app/
  main.py                 --connector <name> runs a connector instead of the window
  main_window.py          source panel, Crossings and Chips tabs, wiring
  models.py               format_time(ms), parse_time(), results line validation
  results_file.py         read and rewrite the results file with a backup
  sources_config.py       data/sources.txt
  connector_protocol.py   encode and decode protocol lines (Qt-free)
  connector_host.py       QProcess wrapper: start, ping, restart with backoff, stop
  connectors/
    __init__.py           registry: names, kinds, labels, stubs, test flags
    runtime.py            the loop a built-in connector runs: hello, commands, events
    dummy_chips.py
    dummy_beam.py
    replay.py
  chips.py                chip map, pass tracker, unknown chips, chip state file
  chip_report.py          the report of Story 6
  http_io.py              + fetch_start_list()
tests/
  test_connector_protocol.py, test_connectors.py, test_connector_host.py,
  test_chips.py, test_chip_report.py, test_results_file.py, test_sources_config.py,
  test_sources_window.py, test_crossings_window.py, test_http_io.py (extended)
```

**Structure Decision**: the existing single-project layout. Logic goes to new Qt-free modules so
the coverage gate measures it; `connector_host.py` uses `QProcess` but no widget and is tested with
real child processes; the window only wires.

## Design notes

- **Window layout**: the action log becomes the first tab of a tab widget, unchanged; "Crossings"
  (the results file: list, Add, Edit, Delete) and "Chips" (start protocol file, Download, Reload,
  dead time, conflicts, unknown chips, Chip report) are the other tabs. An "Event source" group
  above them holds the source choice, the connector choice and its settings, Start/Stop and the
  state line, plus the test-data warning.
- **Beam**: `_on_finish_second_user()` becomes `_stamp_first_empty_slot(time_str, take_next,
  quiet)`, used by the button with the current time, the Next number and dialogs as today, and by a
  beam break with the break's time, no number and `quiet`: a write the shift makes then reports a
  failure in the action log instead of a dialog (FR-011); the shift path stamps slot 5 with the
  given time.
- **Chip pipeline** (window thread, per output chunk): decode events -> for each read: normalise,
  format the time, append the raw line -> `ChipTiming.on_read()` returns new crossings -> each goes
  to `_append_source_crossing()`, which appends, logs and schedules the upload like
  `_write_to_finish()` but never opens a dialog; a crossing it cannot write joins the `unwritten`
  queue, retried every second -> state saved if a crossing was made, else on a 1 s timer.
- **Retro crossings**: after the map changes (download, Reload, start-up), `ChipTiming.set_map()`
  replays, in time order, the raw reads of chips that are in the new map but not attributed, and
  returns the crossings to append.
- **Crossing edits**: the Crossings tab works on a parsed copy of the file; Add/Edit open a small
  dialog (number, time defaulting to now, action); Delete asks first. Each change goes through
  `rewrite_results()`; the in-memory numbers, counts, log and upload follow.
- **Shutdown**: `closeEvent` stops every connector (stop, close stdin, kill after 3 s) before it
  waits for uploads.

## Complexity Tracking

Empty: no constitution violation.
