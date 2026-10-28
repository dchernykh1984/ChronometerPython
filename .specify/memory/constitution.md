<!--
Sync Impact Report
- Version: none -> 1.0.0 (first constitution, written with the event-sources feature of
  ChronometerPython issue #49).
- Principles: I is the maintainer's decision of 2026-10-28 (timing programs only produce
  crossings). II-VI are drawn from CLAUDE.md, AGENTS.md and the skills under .claude/skills and
  .agents/skills (reviewing-a-change, local-gate, site-upload), which stay the detailed runtime
  guidance. VII-VIII are the conventions shared with the sibling repositories.
- Templates: plan-template.md's "Constitution Check" gate reads these principles; no template
  needed changes.
-->

# Chronometer Constitution

The chronometer is the finish judge's tool: it stamps who crossed the line or a control point and
when, writes each crossing to a plain text file next to the program and pushes the file to the
cycling site. A judge stands at the line, riders pass once, and a lost or wrong record cannot be
recorded again.

## Core Principles

### I. Crossings only

The chronometer produces crossings -- `number#time#action#` lines -- by hand, from a light beam or
from timing chips, and nothing else. It does not count laps, rank riders or build a protocol:
FinishProtocolGeneratorPython alone does that (maintainer, 2026-10-28). A feature that needs laps
or results belongs there.

### II. A crossing is never lost

Every crossing is on disk before anything else happens to it. A write that fails keeps the
crossing where the judge can still see it and tells the judge; nothing that can fail -- an upload,
a device, a connector -- may take a crossing with it. A change to a crossing already written keeps
the previous content in a backup first, and is refused if that backup cannot be written.

### III. The judge is never blocked

The interface answers at once. Network calls, device connections and anything that can hang run
outside the interface thread or in another process; a failure is reported in the action log
rather than in a dialog, unless it answers a button the judge just pressed. A connector that
crashes is restarted without the judge's help, and hand timing keeps working meanwhile.

### IV. Files are the source of truth; the network is best effort

The results, groups, start protocol and raw device files next to the program are the record.
Uploads send the whole file as a snapshot with an increasing revision; downloads (groups, the
start protocol) happen only when the judge presses a button, never on their own, so nothing a
network does can change the record during timing.

### V. Formats are a shared contract

`number#time#action#` and `group#time#` lines, the time as `D H:M:S[.mmm]`, are read by
FinishProtocolGeneratorPython, PhotoFinish and the site, and written the same way by
ChronometerAndroid. Start protocol lines are written by StartProtocolMakerPython; the chronometer
reads them by field index and ignores what it does not know. Changing a field, a separator or the
time format is a change for every tool in the set. Old files stay readable: UTF-8, then cp1251,
then Latin-1.

### VI. One folder per event

Runtime files resolve against `app/paths.py:base_dir()`, so a copied folder is one event with its
own settings, files and counters. Paths stored in configs keep their spelling.

### VII. Behaviour is proven by tests

A behaviour change ships with a test that fails without it. Logic lives in Qt-free modules that
the 90% coverage gate measures; the window is excluded from coverage, so a handler change needs a
Qt-level test through the `win` fixture. Tests never touch the repository's data or the network,
and devices are replaced by dummy connectors.

### VIII. Plain, attributable history

Files are ASCII. Commits follow Conventional Commits in one line with no trailers, because
release-please builds the changelog from them. Work is published under the owner's name with no AI
credit anywhere. Every change goes through a pull request from a branch off `origin/main`.

## Constraints

- Python 3.14 and PySide6, run through `uv`; HTTP through the standard library with a 10 second
  timeout. Devices are reached through connectors, separate processes that speak a line protocol,
  so a device library never runs inside the chronometer.
- Portable builds for Windows, macOS (Apple Silicon) and Linux.

## Development Workflow

- A feature that changes a file format, the site exchange or what the judge sees gets a
  specification in `specs/<NNN>-<short-name>/` made with the Spec Kit skills, reviewed by the
  maintainer before implementation.
- `specs/app/` describes the program as it works today; a change that alters described behaviour
  updates it in the same pull request.
- A bug fix or a small change needs no specification of its own.

## Governance

This constitution states the principles; `CLAUDE.md`, `AGENTS.md` and the skills they list hold the
detail and are kept consistent with it. The maintainer amends it through a pull request that bumps
the version -- MAJOR for a principle removed or redefined, MINOR for one added or materially
expanded, PATCH for wording -- and updates the Last Amended date.

**Version**: 1.0.0 | **Ratified**: 2026-10-28 | **Last Amended**: 2026-10-28
