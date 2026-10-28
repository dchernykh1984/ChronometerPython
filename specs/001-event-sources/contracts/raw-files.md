# Contract: raw device files

Plain text, UTF-8, one record per line, `#`-separated and `#`-terminated like the results file.
Append only: a line is never changed. Times are in the results file's format, `D H:M:S.mmm` in
local standard time (with the summer-time option when it is on). An unknown field is left empty.

## Chip reads

`chip#time#device time#antenna#signal#reader#`

- `chip`: normalised id (upper case, ASCII letters and digits).
- `time`: the read's time as the chronometer took it (protocol `time_ms`, else receipt time).
- `device time`, `antenna`, `reader`: as the connector reported them, with `#` and line breaks
  replaced by spaces. `signal`: RSSI in dBm as a decimal number.

ChronometerPython writes it next to the results file as `<results name>.chip_reads.txt`;
ChronometerAndroid as `chip_reads.txt` in its data folder.

## Beam breaks

`sequence#time#device time#`

ChronometerPython: `<results name>.beam_breaks.txt`; ChronometerAndroid: `beam_breaks.txt`.

## Examples

Chip reads:

```text
E28011700000020A#20389 11:35:29.615#1761725729615123#1#-58.5#192.168.1.50#
E2801170000002AB#20389 11:35:29.702##2#-63#192.168.1.50#
```

Beam breaks:

```text
12#20389 11:35:31.004#812345#
```
