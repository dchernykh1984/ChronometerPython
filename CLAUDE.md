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
  No typographic dashes, no quotes-as-glyphs, no Cyrillic in files.
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
