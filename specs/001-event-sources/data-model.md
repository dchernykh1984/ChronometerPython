# Data model: event sources

## Settings (`data/sources.txt`, `key=value`, next to `http_config.txt`)

| Key | Meaning | Default |
| --- | --- | --- |
| `source` | `hand`, `beam` or `chips` | `hand` |
| `beam_connector` | connector name for the beam | `dummy-beam` |
| `chips_connector` | connector name for chips | `dummy-chips` |
| `settings.<connector>` | that connector's settings, one-line JSON | `{}` |
| `custom_command.<kind>` | command line of the `custom` connector, for `beam` or `chips` | empty |
| `dead_time_s` | dead time, 1-120 | `5` |
| `start_protocol` | start protocol file path, kept as typed | `data/start.txt` |

## Connector registry entry

`name`, `kind` (`chips` or `beam`), `label`, `available` (false for stubs), `test` (true for dummy
and replay), default settings.

## Chip read (in memory)

`chip` (normalised), `time` (`D H:M:S.mmm` string), `ms` (that time parsed), `device_time`,
`antenna`, `rssi`, `reader`.

## Chip map

- `bib_of`: chip -> bib, from field 0 and field 11 of every start protocol line (StartProtocolMaker,
  `specs/002-chip-ids/contracts/start-protocol-line.md`).
- `conflicts`: chip -> the bibs of the lines that carry it, when more than one; not in `bib_of`.
- Lines with an empty field 0, `NOT_PAID`, or fewer than 12 separators bind nothing.
- Semicolons in field 11 separate a team's riders: with N > 1 stages and a numeric bib the k-th
  rider binds to bib + k and riders past the N-th bind nothing; otherwise every chip binds to the
  bib.

## Pass

`first`, `last` (milliseconds). Per bib, sorted by `first`, never overlapping within the dead
time. A pass is only ever made together with its crossing, so it never gets another.

## Chip state (`<results name>.chip_state.json`)

```json
{
  "version": 2,
  "processed_lines": 1234,
  "passes": {"15": [[73905615, 73907702]]},
  "pending": {"E2801170000002FF": [[73909100, 73914350, 87]]},
  "unwritten": ["22#20389 11:35:31.004#nextLap#"]
}
```

`unwritten`: crossings made but not yet in the results file, retried every second.

`pending`: reads of chips the map did not bind when they came (unknown, or on two bibs), per chip
as runs `[first, last, count]` of reads less than the dead time apart, so a chip left by the
antenna for hours is one run. When a new map binds one, its runs join the bib's reads (FR-010):
runs less than the dead time apart form one group, a group near a pass joins it and makes
nothing, and a group near none is a new pass, its crossing at its first read. A pass is `[first, last]`: every pass exists because it made a
crossing, so it needs no flag for that. A state of another `version` is rebuilt from the raw
reads file.

## Unknown chip (derived)

`chip`, `first`, `last`, `count`: from the raw reads of chips not in `bib_of`, rebuilt at start-up
and kept up to date.

## Crossing

A results file line `number#time#action#`; `action` is `nextLap`, `finish`, `nextStage`, `DSQ` or
`DSQ: <reason>`.

## Results backup

`temp/results<unix time>_<n>.txt`: the whole results file before a change.

## Start protocol backup

`temp/start<unix time>_<n>.txt`: the start protocol file before a download replaces it.
