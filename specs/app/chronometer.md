# The chronometer as it works today

Written from the code (`app/main_window.py`, `app/models.py`, `app/http_io.py`, `app/paths.py`) on
2026-10-28 and brought up to date with the event sources of `specs/001-event-sources` on
2026-10-29. Where the code does not say why, this file does not guess.

## Slots

Five slots on the left, each a number field and a time field. The time field holds
`<time>#<action>`, so a saved slot becomes `number#time#action#` in the results file.

- **F** (or Enter in an empty-time number field) stamps the current time and the action into that
  slot and moves focus to the next number field.
- **S** appends the slot to the results file and clears it; a failed write keeps the slot and
  shows a dialog.
- **Save All and Clear** writes every filled slot; **Save+Shift** writes slot 1, moves slots 2-5 up
  and fills slot 5 with the "Next" number stamped now; Enter in "Next" does the same, Ctrl+Enter
  stamps `nextStage` instead of the action.
- **Finish ALL empty** stamps every slot without a time; **Clear all** empties the slots after a
  confirmation.
- **Finish mode** chooses the action: `finish` when checked, `nextLap` otherwise.
- **Second user mode** enables a big FINISH button that stamps the first slot without a time (or
  shifts when all are stamped); a second person presses it while the judge types numbers.
- **Crosses** shows how often each slot's number already appears in the results file and the slots;
  "FINISH ALL" lights up when one reaches **Max laps**. This is a hint for the judge only.
- A **beam break** stamps the first slot without a time with the break's time, as FINISH does,
  but never takes the "Next" number: when every slot has a time, slot 1 is written, the others
  move up and the last one gets the break's time and no number. A write it causes that fails is
  reported in the action log, not in a dialog.

## Event source

The "Event source" group chooses where crossings come from: **By hand** (the slots alone, the
default), **Light beam** or **Timing chips**. The last two run a connector, a separate program that
reports what a device sees: **Device** picks it, **Settings** holds its settings as one-line JSON
(for "Custom command", the command line).

- Connectors today: "Test beam" and "Test chips" make events up, and a red "TEST CONNECTOR" warning
  shows while one runs; "Replay a chip reads file" plays a raw reads file back; "Custom command"
  runs any program that speaks `specs/001-event-sources/contracts/connector-protocol.md`. LLRP,
  RaceResult, R2000, USB beam and Bluetooth beam are listed as "not available yet".
- A connector starts only on **Start**, also after the program restarts, and stops on **Stop** or
  when the window closes. The line under the buttons shows its state.
- A connector that exits, fails to start, says no hello within 10 s or answers no ping for 15 s is
  started again after 1 s, then 2, 4 and so on up to 30 s while it keeps failing, and after 30 s
  of steady running the pause is back to 1 s. One that speaks another protocol version or is of
  the other kind is stopped for good, and the state says why.
- The built-in connectors are this program run again as `<program> --connector <name>`
  (`python -m app.main --connector <name>` in a checkout); Qt is not loaded for them.

### Timing chips

- Every read goes to the raw reads file first, whether its chip is known or not.
- Chips map to bibs from field 11 of the start protocol file: commas separate one rider's ids,
  semicolons the riders of a team in stage order, and on a line with more than one stage and a
  numeric bib the k-th rider binds to bib + k. Ids compare upper case, ASCII letters and digits
  only. A chip on two bibs binds to neither.
- A bib's reads less than the dead time apart are one pass. A read that starts a pass makes a
  crossing at once, at its own time, with the action the finish mode gives; a crossing is never
  moved, and one the judge deleted does not come back.
- Reads of chips the map does not bind wait, and are timed when a newer start protocol binds them.
- Chip crossings are written without dialogs. One that cannot be written waits, is retried every
  second, and the Chips tab says in red how many wait.
- The chip state is kept next to the results file, so a restart neither times a pass twice nor
  forgets one; reads the raw file got after the last save (a crash) are replayed at start.

## Tabs

Under the slots:

- **Action log**: every line written (crossings and groups), every upload result, connector states
  and errors, and every correction. It is not read back from the files.
- **Crossings**: the results file as it is now. **Add**, **Edit** and **Delete** work in any mode:
  the file is first copied to `temp/results<unix time>_<n>.txt`, a change is refused when that copy
  fails, and the new file then replaces the old one in one step. The action is `nextLap`,
  `finish`, `nextStage`, `DSQ` or `DSQ: <reason>`; a device never writes a DSQ.
- **Chips**: the start protocol file (**...**, **Reload**, **Download start protocol from the
  site**), how many chips of how many bibs it maps, the dead time (5 s by default), chips on two
  bibs, unknown chips with their reads, and **Chip report**, which writes for each bib's chips in
  how many of its passes each was read and how often, the chips never read, the unknown ones and
  those on two bibs.

## DSQ and groups

- **DSQ** appends `number#time#DSQ#` or `number#time#DSQ: <reason>#` (`#` and line breaks stripped
  from the reason).
- **Group start**: "Start" stamps the time; "Save group" appends `group#time#` to the groups file,
  removes the group from the list and keeps the time for the next group.

## Files

All runtime paths resolve against `app/paths.py:base_dir()`: the folder holding the program when
frozen (on macOS the folder holding the `.app`), the working directory in development.

- `data/groupsList.txt`: group names, one per line, then `configFiles`, the results file path and
  the groups file path. "Load race config" reads another one.
- Results file and groups file: paths chosen in the UI (frozen by default), appended line by line.
- `data/http_config.txt`: `site_url`, `token`, `device_id`, `point_number`, `rev_finish`,
  `rev_group`, as `key=value`. A device id is generated on first use. Never committed.
- `temp/stc<unix time>.txt`: a backup after every slot action unless "Disable backup" is checked:
  the action log, `group#time#`, then each slot as `number#time#action#`.
- `data/sources.txt`: the event source, each connector's settings, the dead time and the start
  protocol path, as `key=value`.
- The start protocol file: chosen in the Chips tab, `data/start.txt` by default. It is read when
  chosen, on Reload, at start and after a download, never in between.
- Next to the results file and named after it (`results.txt` gives `results.chip_reads.txt`):
  - `.chip_reads.txt`: `chip#time#device time#antenna#signal#reader#`, every chip read;
  - `.beam_breaks.txt`: `sequence#time#device time#`, every beam break;
  - `.chip_state.json`: the passes, the waiting reads and the crossings not yet written;
  - `.chip_report.txt`: the last chip report.
- `temp/results<unix time>_<n>.txt` and `temp/start<unix time>_<n>.txt`: the results file before a
  correction, the start protocol file before a download.
- Reading tries UTF-8, then cp1251, then Latin-1, for files from the older C++ chronometer.

## Time

`D H:M:S.mmm`: whole days since 1970-01-01 and the time of day, in local standard time, without
zero padding; "Summer time (+1h)" adds an hour when the system reports daylight saving.

## Site exchange

Only when the site URL, token and device id are all set; otherwise nothing is sent.

- After a results write (400 ms debounce) the whole results file goes to
  `POST /api/v1/finish-times/` (point 0) or `POST /api/v1/remote-points/` (point N), with the
  device id and an increasing `client_revision` (`rev_finish`).
- "Save group" sends the whole groups file to `POST /api/v1/group-times/` (`rev_group`).
- "Get groups" reads group names from `GET /api/v1/participants/` and replaces the list.
- A correction in the Crossings tab uploads the whole results file as a write does.
- "Download start protocol from the site" reads `GET /api/v1/start-list/`, the lines every device
  uploaded, merged, into the start protocol file, and only on that button. An error or an empty
  list changes nothing.
- Uploads and the download run on a `QThread`. An upload's result and a finished download go to
  the action log, a failed download to a dialog. Closing the window waits for them.
