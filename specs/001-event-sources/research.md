# Research: event sources

## 1. Connectors as child processes driven by QProcess

- **Decision**: each connector is a child process started with `QProcess`; its output is read in
  the Qt event loop through `readyReadStandardOutput`, its exit through `finished`, its liveness
  through a `ping` every 5 s.
- **Rationale**: a device library or a hung socket in another process cannot freeze or crash the
  window (constitution III); `QProcess` needs no thread of our own and works the same on the three
  platforms; a frozen build starts a connector by running itself with `--connector <name>`, so no
  second executable is shipped.
- **Alternatives**: threads in the chronometer (rejected: a C extension that hangs or crashes takes
  the window with it); `multiprocessing` (rejected: its spawn start-up in a frozen onefile build is
  fragile and still needs a message format); a local TCP socket (rejected: ports and firewalls for
  no gain over pipes).
- **Risk**: the Windows build is `--windowed --onefile`. A GUI-subsystem child still gets the
  pipes `QProcess` hands to `CreateProcess`, and the onefile loader unpacks on every start (about a
  second). The build workflow smoke-runs a connector from the frozen app on every platform.

## 2. JSON lines with an explicit version

- **Decision**: UTF-8 JSON objects, one per line, `hello` carrying `protocol: 1`
  ([contract](contracts/connector-protocol.md)).
- **Rationale**: any language can speak it (a microcontroller, a vendor SDK in C#, a shell
  script); readable in a log; unknown fields ignored lets the protocol grow. The Android app reports
  the same events, so one description serves both.
- **Alternatives**: the raw-file line format on the wire (rejected: no room for status, errors and
  pings); protobuf (rejected: a dependency and a build step for a few messages a second).

## 3. Time on the wire: Unix milliseconds on the chronometer's clock

- **Decision**: `time_ms` is optional Unix time in milliseconds on the host clock; without it the
  host stamps the receipt time. The device's own time travels as opaque text, `device_time`.
- **Rationale**: Unix milliseconds have no time zone or summer-time ambiguity; the chronometer
  formats them exactly as it formats its own clock. Readers' clocks differ (microseconds since the
  epoch for LLRP, tick counts for a beam), so only the connector can map them, and only once it
  knows the device.

## 4. Passes as intervals, kept in a state file

- **Decision**: per bib, a sorted list of passes `[first, last]` in milliseconds of the results
  file's time scale. A read at `t` joins every pass with `first - dead < t < last + dead` (merging
  them, making nothing), else starts a new one, whose crossing is made at once at `t`. Reads of
  chips the map does not bind wait in a pending list. The passes, the pending reads, the crossings
  waiting to be written and the number of raw lines processed are saved to
  `<results name>.chip_state.json` after every crossing and once a second otherwise.
- **Rationale**: intervals give FR-009's gap rule in any arrival order; a pass remembers that it
  was issued, so a crossing the judge deleted is never made again (spec, US3 and Android US6);
  passes formed under one dead time keep their shape when it changes. At start-up the state is
  loaded and the raw lines after the processed count are replayed, so a crash loses nothing.
- **Alternatives**: recomputing passes from the raw file at every start (rejected: a changed dead
  time would regroup history and make crossings again); the results file as the memory (rejected:
  the judge edits it).
- **Known limit**: the crossing is written before the state that records it, so a crash between the
  two can repeat that one crossing on restart; it can never be lost (constitution II).

## 5. Times in the chip logic come from the raw line

- **Decision**: the pass logic works on the millisecond value of the formatted time written to the
  raw file (`D H:M:S.mmm` parsed back), not on `time_ms`.
- **Rationale**: live reads and the reads replayed for retro crossings then share one scale, with
  the summer-time option applied the same way.

## 6. Files next to the results file

- **Decision**: `<results name>.chip_reads.txt`, `<results name>.beam_breaks.txt`,
  `<results name>.chip_state.json`, `<results name>.chip_report.txt` in the results file's folder.
  The start protocol file is chosen in the window (default `data/start.txt`).
- **Rationale**: the spec puts the raw files "next to the results file"; deriving the names keeps
  two results files in one folder apart, and a new results file starts a fresh chip state.

## 7. Rewriting the results file

- **Decision**: copy the current file to `temp/results<unix time>_<n>.txt` (a free `n`); refuse the
  change if the copy fails; write the new content to a temporary file in the same folder, flush,
  `fsync`, then `os.replace`. All writes to the results file happen on the window's thread, so an
  append from a chip crossing never interleaves with a rewrite.
- **Rationale**: FR-014; `os.replace` is atomic on the three platforms within one folder.
- **Windows**: a program that has the file open without delete sharing -- PhotoFinish reading it,
  an editor, an antivirus scan -- makes `os.replace` fail with a permission error. The rewrite
  retries for up to 0.5 s before it reports the failure: it waits on the window's thread, where a
  hand stamp waits too. The backup is kept either way, and the results file is never left half
  written.

## 8. Crossing counts follow the file

- **Decision**: the window keeps the results file's numbers in memory, refreshed after every write
  and when the path changes, and counts from them and the slots.
- **Rationale**: FR-015; the action log is not the record once crossings can be edited. Counting
  from the file also keeps the counts right after a restart, which the log never did. This changes
  hand-mode behaviour described in `specs/app/chronometer.md`, so SC-004 is reworded in the spec's
  review and the description is updated with the code.

## 9. Download of the start protocol

- **Decision**: `fetch_start_list()` in `app/http_io.py`, the same request FinishProtocolGenerator
  makes, run on the worker thread uploads use. An empty list is a failure ("nothing uploaded yet"),
  so a premature press cannot wipe a good file.
- **Rationale**: FR-008; one more stdlib call with the existing 10 s timeout.

## 10. Test connectors and stubs

- **Decision**: built in: `dummy-chips`, `dummy-beam`, `replay` (a chip reads file played back at
  its own pace, or faster), `custom` (a command line). Stubs: `llrp`, `raceresult`, `r2000`,
  `beam-usb`, `beam-ble`, listed and disabled. While a dummy or replay connector feeds the results
  file, the window shows a warning that its crossings are test data.
- **Rationale**: the maintainer has no reader yet (decision 5 of 2026-10-28); the dummies exercise
  every path a real device will use, and the warning keeps a rehearsal from being uploaded as a race
  unnoticed.
