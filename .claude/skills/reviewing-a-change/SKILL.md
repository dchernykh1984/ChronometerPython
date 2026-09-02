---
name: reviewing-a-change
description: What to look for when reviewing a diff in this repository - the failure modes that actually matter for live race timing. Use before pushing your own change and when asked to review a PR or a diff here.
---

# Reviewing a change

`/code-review` handles the generic pass. This skill is about what is specific
to a chronometer: a judge is standing at a finish line, riders cross once, and
a lost or wrong record cannot be re-recorded. Read the diff asking what it does
when something goes wrong, not whether the happy path works.

## The questions that find real bugs here

**Can a crossing be lost?** Every write path returns a bool that the caller
must respect. `_write_to_finish` returns `False` when the results file is
missing or unwritable, and its callers only clear the slot when it returned
`True`; `_shift_fields_up` aborts the shift on a failed write for the same
reason. A change that ignores one of those return values silently drops a
finish time. Same question for a `try`/`except` that swallows an `OSError`.

**Does the judge find out?** A failure that only lands in a log the judge is
not watching is a failure they will discover after the race. File errors raise
a dialog; upload errors are appended to the action log on purpose, because the
network is best effort and a modal dialog mid-race is worse than a missed
upload.

**Does anything slow down or block the UI thread?** Timing runs on a 1ms
`QTimer`. Uploads live on a `QThread` for exactly this reason, and
`closeEvent` waits for the running ones because destroying a live `QThread`
aborts the app. Never move network or disk-heavy work back onto the handler.

**Does it change the on-disk format?** `number#time#action#` and
`group#time#` lines are read by other tools in the offline_referee set and by
the site. Adding a field, reordering, or changing the separator is a breaking
change even though nothing in this repo will complain.

**Does it change where data lives?** `app/paths.py:base_dir()` is what makes
one copied folder per event work. A change that resolves a path against the
current working directory instead would make two events share one file.

**Are the reads still tolerant?** Files written by the older C++ chronometer
turn up in cp1251; every reader tries utf-8, then cp1251, then latin-1. Do not
narrow that to utf-8.

**Does it touch the upload revision counters?** They are the server's only
protection against a stale snapshot overwriting a newer one. See the
`site-upload` skill before changing anything about them.

## Tests

A change to `models.py`, `http_io.py` or `paths.py` needs a unit test - those
are what the 90% coverage gate measures. A change to a `main_window.py`
handler needs a Qt-level test through the `win` fixture in `tests/conftest.py`,
even though `main_window.py` is omitted from coverage. The omission is why the
handler tests matter: nothing else notices when a handler drifts.

## Scope

Report what you find outside the scope of the task; do not fix it. This code
writes race results, and an unrequested edit next to a requested one is hard to
review and easy to distrust.
