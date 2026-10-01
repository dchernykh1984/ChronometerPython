---
name: site-upload
description: How the chronometer pushes timing data to the cycling site, and how to diagnose "the site is not getting my times". Use for any question or change touching http_io.py, the Site upload (HTTP) panel, device ids, or the revision counters.
---

# Site upload

The results and groups files are the source of truth. The upload is a best
effort mirror of them, so a race is never blocked by the network.

## Settings

`data/http_config.txt`, `key=value`, resolved next to the runnable
(`app/paths.py:base_dir()`), so every copied event folder has its own:

| Key | Meaning |
| --- | --- |
| `site_url`, `token` | The competition on the site. The token is a secret. |
| `device_id` | This machine. Generated and persisted on first load. |
| `point_number` | `0` = finish line, `1..N` = a remote control point. |
| `rev_finish`, `rev_group` | Per-stream revision counters. |

If `site_url`, `token` or `device_id` is empty, uploads are skipped silently -
no log line, no dialog. That is the first thing to check.

## What is sent, and when

Each upload posts the **whole file** as `items`, keyed by `device_id`, with the
next `client_revision`. Re-posting the same `device_id` overwrites the stored
snapshot; the server rejects an older revision with HTTP 409.

| Trigger | Endpoint |
| --- | --- |
| A record is appended to the results file (`_write_to_finish`) | `/api/v1/finish-times/` if `point_number` is 0, else `/api/v1/remote-points/` |
| "Save group" (`_on_save_group`) | `/api/v1/group-times/` |
| "Get groups" - a read, not an upload | `/api/v1/participants/` |

Two consequences worth knowing:

- **Pressing `F` uploads nothing.** `F` only stamps the time into the slot. The
  upload happens when the record is saved (`S`, `Save All and Clear`,
  `Save+Shift`, `DSQ`, or the automatic shift), which is what appends the line
  to the file.
- **Nothing is pushed at startup**, and a failed upload is never retried on its
  own. Because every upload is a full snapshot, the next successful save
  catches up everything written before it - including records made while the
  token was still empty.

Finish uploads are debounced 400ms so a batch save is one request. Uploads run
on a `QThread` (`_UploadWorker`); `closeEvent` waits for them.

## Diagnosing "the times are not on the site"

Read the in-app action log. Every upload appends one line there and nothing
else surfaces it:

- `site: uploaded N item(s)` - the server stored N. N is the number of lines in
  the whole file, not the number of new records.
- `site upload error: Connection error: ...` - offline. The record is safely in
  the file; the next successful save re-sends everything.
- `site upload error: HTTP 409` - the server holds a newer revision for this
  `device_id` than the one just sent. Normally means the folder was copied or
  restored with a counter behind what that device already sent. Generate a new
  Device ID, or raise `rev_finish` / `rev_group` past the server's value.
- `site upload error: HTTP 4xx` on everything - wrong token or site URL.
- No line at all after a save - one of the three required fields is empty, or
  the record was never saved (see `F` above).

Also check **Point number**: with a non-zero value the times go to the remote
point endpoint, so they will not appear as finish times.

## Changing this code

The server side lives in the `cycling-site` repository; the request shapes have
to match it. Keep the 10s timeouts (an offline machine must fail fast rather
than hang), keep every network call off the UI thread, and keep failures in the
action log rather than in a modal dialog. `tests/test_auto_upload.py` and
`tests/test_http_io.py` cover this path - extend them rather than adding a live
call.
