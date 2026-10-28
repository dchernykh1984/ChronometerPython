# Data model: event sources

## Settings (`data/sources.txt`, `key=value`, next to `http_config.txt`)

| Key | Meaning | Default |
| --- | --- | --- |
| `source` | `hand`, `beam` or `chips` | `hand` |
| `beam_connector` | connector name for the beam | `dummy-beam` |
| `chips_connector` | connector name for chips | `dummy-chips` |
| `settings.<connector>` | that connector's settings, one-line JSON | `{}` |
| `custom_command` | command line of the `custom` connector | empty |
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

`first`, `last` (milliseconds), `issued` (a crossing was made for it once). Per bib, sorted by
`first`, never overlapping within the dead time.

## Chip state (`<results name>.chip_state.json`)

```json
{
  "version": 1,
  "processed_lines": 1234,
  "attributed": ["E28011700000020A", "E2801170000002AB"],
  "passes": {"15": [[73905615, 73907702, true]]},
  "unwritten": ["22#20389 11:35:31.004#nextLap#"]
}
```

`unwritten`: crossings made but not yet in the results file, retried every second.

`attributed`: chips whose reads have been put into passes; a chip in the map but not here is
"newly known" and its reads in the raw file are replayed into passes (FR-010).

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
