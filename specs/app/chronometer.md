# The chronometer as it works today

Written from the code (`app/main_window.py`, `app/models.py`, `app/http_io.py`, `app/paths.py`) on
2026-10-28, before the event-sources feature. Where the code does not say why, this file does not
guess.

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
- Reading tries UTF-8, then cp1251, then Latin-1, for files from the older C++ chronometer.

## Action log

A list under the slots showing every line written (crossings and groups) and every upload result.
It is not read back from the files.

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
- Uploads run on a `QThread`; their result is written to the action log. Closing the window waits
  for running uploads.
