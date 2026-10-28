# Tasks: Event sources -- by hand, light beam and timing chips

Each task is one commit with the message shown; the tests that prove a task are part of it. Before
each commit: `uv run pre-commit run --all-files` and `uv run pytest`.

## Phase 1: the results file as something the judge can correct (US3)

- [ ] T001 `format_time(ms, summer_time)` and `parse_time(text)` in `app/models.py`;
  `get_current_time()` uses `format_time`. Unit tests, including summer time and milliseconds
  padding. -- `refactor(time): format any moment, not only the current one`
- [ ] T002 `app/results_file.py`: `read_results()`, `validate_crossing()`, `rewrite_results()`
  (backup to `temp/results<time>_<n>.txt`, refuse without it, temporary file, fsync,
  `os.replace`). Unit tests: backup content, refusal, atomicity on a failing write, validation.
  -- `feat(results): rewrite the results file only after a backup of it`
- [ ] T003 [US3] "Crossings" tab: the results file as a list; Add (number, time defaulting to now,
  action), Edit, Delete with confirmation; each change through `rewrite_results()`, logged and
  uploaded. Qt tests through `win`. -- `feat(crossings): add, edit and delete crossings of the results file`
- [ ] T004 [US3] Crossing counts from the results file and the slots (in-memory numbers refreshed
  on every write and path change); update `specs/app/chronometer.md`. Qt tests.
  -- `feat(crossings): count a number's crossings from the results file`

## Phase 2: connectors (US5)

- [ ] T005 [US5] `app/connector_protocol.py`: decode an output line into an event or a reason to
  ignore it, encode commands, limits from the contract. Unit tests for every message and every
  malformed case. -- `feat(connectors): encode and decode the connector protocol`
- [ ] T006 [US5] `app/connectors/runtime.py`, `dummy_chips.py`, `dummy_beam.py`, registry; `app/main.py`
  runs `--connector <name>` without Qt. Unit tests drive the runtime with in-memory streams.
  -- `feat(connectors): run test chips and test beam connectors from the chronometer itself`
- [ ] T007 [US5] `app/connectors/replay.py`: a chip reads file played at its pace times `speed`.
  Unit tests. -- `feat(connectors): replay a chip reads file as a connector`
- [ ] T008 [US5] `app/connector_host.py`: start (built-in or custom command), hello timeout, ping and
  pong, restart 1-30 s with reset after 30 s, stop with a 3 s grace, state signals. Tests with real
  child processes: crash, hang, bad lines, stop, custom command.
  -- `feat(connectors): start, watch and restart connector processes`
- [ ] T009 [US5] `app/sources_config.py` (`data/sources.txt`); "Event source" group: source,
  connector (stubs disabled and marked "not available yet"), settings, Start/Stop, state line,
  test-data warning; `closeEvent` stops connectors. Qt tests.
  -- `feat(sources): choose the event source and its connector`

## Phase 3: beam (US4)

- [ ] T010 [US4] `_stamp_first_empty_slot(time_str)` shared by the second-user button and beam
  breaks; every break appended to `<results name>.beam_breaks.txt` first. Qt tests with the test
  beam. -- `feat(beam): stamp the first empty slot with each beam break and keep every break`

## Phase 4: chips (US1, US2)

- [ ] T011 [US2] `app/chips.py`: `normalise_chip()`, `build_chip_map()` with conflicts and the lines
  that bind nothing; "Chips" tab with the start protocol file, Reload, counts and conflicts. Unit
  and Qt tests. -- `feat(chips): map chips to bibs from the start protocol file`
- [ ] T012 [US1] Pass tracker, `ChipTiming.on_read()`, chip state file with replay of unprocessed raw
  lines, dead time setting; reads appended to `<results name>.chip_reads.txt` before processing;
  crossings through `_write_to_finish()`. Tests: every case of `contracts/chip-pass-vectors.json`,
  state round trip, crash between raw line and state. Qt test with the test chips.
  -- `feat(chips): turn chip reads into crossings with a dead time`
- [ ] T013 [US2] Unknown chips (first, last, count) in the Chips tab; `ChipTiming.set_map()` times
  newly known chips from their raw reads. Tests from the vectors and a Qt test.
  -- `feat(chips): list unknown chips and time them once the start protocol knows them`
- [ ] T014 [US2] `fetch_start_list()` in `app/http_io.py`; "Download start protocol" on the worker
  thread; backup to `temp/start<time>_<n>.txt`, atomic write, map rebuilt, summary logged; failures
  (network, HTTP, invalid, empty) change nothing. Unit tests with a fake `urlopen`, Qt tests.
  -- `feat(site): download the start protocol into its file by a button`

## Phase 5: report (US6)

- [ ] T015 [US6] `app/chip_report.py` and the "Chip report" button writing
  `<results name>.chip_report.txt`. Unit tests with the reads of US1.
  -- `feat(chips): report how many chips each rider's passes were read with`

## Phase 6: build and documentation

- [ ] T016 Smoke-run a built-in connector from the frozen app on every platform in
  `.github/workflows/build.yml` (start it, read `hello`, send `stop`); adjust
  `tests/test_build_workflow.py`. -- `ci(build): check that the frozen app runs a connector`
- [ ] T017 `specs/app/chronometer.md`: sources, Crossings and Chips tabs, the new files, the
  download; README's user section. -- `docs: describe event sources, corrections and the chip files`

## Dependencies

T001 -> T002 -> T003 -> T004. T005 -> T006 -> T007, T006 -> T008 -> T009 -> T010.
T009 and T001 -> T011 -> T012 -> T013 -> T014. T012 -> T015. T016 after T006. T017 last.
