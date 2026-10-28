# Quickstart: trying the event sources without hardware

1. `uv run python -m app.main`, choose a results file as usual.
2. **Beam**: Event source -> Light beam, connector "Test beam", Start. Every few seconds a break
   stamps the next empty slot; type the number and save as usual. The breaks are also in
   `<results name>.beam_breaks.txt`.
3. **Chips**: write a start protocol with chips (StartProtocolMaker, or by hand):

   ```text
   15#Rider A#M40#3#1#1985####0 00:00:00.000##A1,A2#
   22#Rider B#M40#3#1#1990####0 00:00:00.000##B1#
   ```

   Chips tab -> start protocol file -> that file, Reload. Event source -> Chips, connector
   "Test chips", Start. Crossings for 15 and 22 appear in the results file, one per pass; every
   read is in `<results name>.chip_reads.txt`; the unknown chip the test connector reads now and
   then is listed under Chips.
4. **Replay**: connector "Replay", settings `{"path": "<a chip reads file>", "speed": 10}` plays a
   recorded race ten times faster.
5. **Download**: with the site URL and token set, "Download start protocol" fetches what
   StartProtocolMaker uploaded; the previous file is kept in `temp/`.
6. **Corrections**: Crossings tab -> Add / Edit / Delete; each change leaves a backup
   `temp/results<time>_<n>.txt`.
7. **A connector that fails**: connector "Custom", command `python -c "raise SystemExit(1)"`: the
   state line shows it restarting after 1 s, 2 s, 4 s...; hand timing keeps working.
