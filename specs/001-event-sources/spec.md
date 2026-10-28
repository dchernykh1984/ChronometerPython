# Feature Specification: Event sources -- by hand, light beam and timing chips

**Feature Branch**: `feat/event-sources`

**Created**: 2026-10-28

**Status**: Draft

**Input**: Issue [#49](https://github.com/dchernykh1984/ChronometerPython/issues/49), comments 1-8.
Maintainer's decisions of 2026-10-28:

- One chronometer with a choice of event source: by hand, light beam or chips. Beam and chips are
  reached through connectors, separate processes; a connector that fails never takes the
  chronometer down.
- Programs that time only produce crossings; laps and protocols are FinishProtocolGenerator's job.
- The bib-to-chip binding comes from the start protocol (field 11, written by
  StartProtocolMaker). The chronometer reads it from a start protocol file; a button downloads into
  that file the start list StartProtocolMaker uploaded to the site, before the start, never on its
  own.
- Chip reads of one bib that follow each other within the dead time are one crossing: a new
  crossing needs 5 seconds of silence from all of the bib's chips (configurable).
- Every chip read is kept in a raw file of its own, so it can be checked afterwards how many chips
  worked.
- In any mode the judge can quickly add, edit or delete a crossing; DSQ stays a hand entry.
- No real reader or Bluetooth device yet: stubs, and dummy connectors to test with. The connector
  interface must be enough for LLRP readers (Impinj, Zebra), the RaceResult decoder and the cheap
  R2000 readers with their own protocols.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Chip reads become crossings (Priority: P1)

The judge selects the chip source and starts it. Every rider who passes the antennas gets one
crossing in the results file, `number#time#action#`, uploaded to the site like a hand-timed one.
The action follows the finish-mode switch, as for a hand-timed crossing. A rider usually carries
two or three chips and each is read many times; all reads of one bib's chips that follow each other
within the dead time are one crossing, timed at the first read. Every read, of known and unknown
chips alike, is appended to the raw reads file.

**Why this priority**: It is what chip timing is for; everything else supports it.

**Independent Test**: With a start protocol that binds chips A and B to bib 15, feed reads at
0.0 s (A), 0.3 s (B), 2.0 s (A) and 9.0 s (A) through the replay connector: the results file gets
`15#<time of the 0.0 s read>#nextLap#` and `15#<time of the 9.0 s read>#nextLap#`, and the raw reads
file has four lines.

**Acceptance Scenarios**:

1. **Given** chips A and B bound to bib 15, **When** reads arrive at 0.0 s (A), 0.3 s (B) and
   2.0 s (A), **Then** there is one crossing for 15, at the time of the 0.0 s read.
2. **Given** that crossing, **When** A is read again 7 s after the last read, **Then** a second
   crossing for 15 is written.
3. **Given** a rider standing near the check-in antenna of the start corral, read every second for
   a minute, **Then** there is one crossing.
4. **Given** the dead time set to 10 s, **Then** the 10 s rule replaces the 5 s one.
5. **Given** finish mode checked, **Then** chip crossings carry `finish`, as hand-timed ones do.
6. **Given** any read, known or unknown, **Then** the raw reads file gets one line with the chip id,
   the time, and what the device reported (device time, antenna, signal strength, reader).

---

### User Story 2 - The start protocol: a file, refreshed from the site by a button (Priority: P1)

Before the start, while there is a network, the judge presses "Download start protocol". The
chronometer fetches the start list StartProtocolMaker uploaded to the site and saves it as the
start protocol file, then rebuilds the map from chip to bib. In the forest nothing is downloaded:
the file is already there. A chip bound to two bibs is reported and left out. A chip that is not in
the map is listed as unknown. When the map changes, the earlier reads of chips that just became
known turn into their crossings.

**Why this priority**: Without the map no read can become a crossing, and a desk that forgot a chip
must not cost a rider their crossings.

**Independent Test**: Read unknown chip C at 10:00:00, then download a start protocol that binds C
to bib 22: the results file gets `22#<10:00:00 read time>#...#`.

**Acceptance Scenarios**:

1. **Given** the site URL, token and an uploaded start list, **When** the judge presses
   "Download start protocol", **Then** the start protocol file holds the uploaded lines, the
   previous file is kept as a backup, and the judge sees how many chips and bibs were loaded.
2. **Given** no network, an HTTP error, an invalid response or a start list with no lines, **When**
   the judge presses it, **Then** a message says why; the file and the map are unchanged.
3. **Given** a chip on two lines, **Then** it is reported with both bibs and its reads are not
   attributed to either.
4. **Given** an unknown chip, **Then** it is listed with its first and last read and the number of
   reads, until the map binds it.
5. **Given** a chip that was unknown when read, **When** a later map binds it, **Then** its earlier
   reads become crossings by the same dead-time rule, appended to the results file.
6. **Given** a missing or unreadable start protocol file, **Then** the chip source says so, still
   keeps every read in the raw file, and writes no crossing.
7. **Given** the program starts, **Then** it reads the start protocol file it used last; it never
   contacts the site on its own.

---

### User Story 3 - Quick corrections by hand, in any mode (Priority: P1)

The judge sees the crossings of the results file in a list and can add one (a rider seen passing
without a crossing), edit one (wrong number or time) or delete one (a false read). Every change
keeps the previous file in a backup first and then rewrites the results file; the next upload sends
the new snapshot. DSQ stays a hand entry, as today.

**Why this priority**: Chips and beams make mistakes no judge can prevent; without a quick fix at
the line the protocol inherits them.

**Independent Test**: Delete one crossing, add one and edit one: the results file shows the three
changes, three backups hold the earlier versions, and the upload after each change sends the
current file.

**Acceptance Scenarios**:

1. **Given** a false chip crossing, **When** the judge deletes it and confirms, **Then** the results
   file no longer has it and a backup holds the file as it was before.
2. **Given** a rider seen without a crossing, **When** the judge adds bib 23 at 10:01:02.300,
   **Then** `23#<that time>#nextLap#` is appended.
3. **Given** a crossing for 15, **When** the judge changes its number to 51, **Then** that line
   changes in place and nothing else does.
4. **Given** a time that is not a valid `D H:M:S[.mmm]`, **Then** the edit is refused and the file is
   unchanged.
5. **Given** the backup cannot be written, **Then** the change is refused and the judge sees why.
6. **Given** a change, **Then** the crossing counts shown next to the slots follow the file.
7. **Given** a chip crossing the judge deleted as false, **When** more reads of the same pass arrive
   or the start protocol changes, **Then** the crossing is not made again.

---

### User Story 4 - Light beam breaks fill the slots (Priority: P2)

With the beam source started, every break of the beam puts its time into the first slot without a
time -- what the second-user FINISH button does today -- and the judge types the number and saves
as usual. Every break is also appended to a raw beam file, so no break is lost when the judge
clears a slot.

**Why this priority**: Time trials and downhill start and finish one rider at a time; the beam
times them better than a thumb. It needs the connector contract of Story 5, so it follows the chip
work.

**Independent Test**: Start the dummy beam; each break stamps the next empty slot with its own time
and appears in the raw beam file.

**Acceptance Scenarios**:

1. **Given** empty slots, **When** a break arrives at 10:00:00.123, **Then** slot 1's time becomes
   `<that time>#<action>`.
2. **Given** all slots stamped, **When** another break arrives, **Then** the slots shift as with the
   second-user button, the oldest stamped slot is written, and slot 5 gets the break's time without
   a number; what the judge is typing in Next stays there.
3. **Given** any break, **Then** the raw beam file gets a line with its time and sequence number.

---

### User Story 5 - A failing source never stops timing (Priority: P2)

Connectors run as separate processes. The judge sees each one's state: running, restarting,
stopped, not available. A connector that crashes or hangs is restarted with a growing pause, and
hand timing keeps working throughout. The real devices are listed but marked "not available yet";
the dummy and replay connectors work today, and a custom command runs any program that speaks the
connector protocol.

**Why this priority**: A device fault in the middle of a race must not cost the judge the race.

**Independent Test**: Kill the dummy connector's process: the action log reports it, it comes back,
and the slots worked all the time.

**Acceptance Scenarios**:

1. **Given** a running connector, **When** its process dies, **Then** the log says so and it is
   started again after 1 s, then 2 s, 4 s and so on up to 30 s while it keeps failing; once it has
   run for 30 s without failing, the next pause is 1 s again.
2. **Given** a connector that sends a line that is not valid protocol, **Then** the line is logged
   and ignored.
3. **Given** a stub (LLRP / Impinj, RaceResult, R2000, USB beam, Bluetooth beam), **Then** it is
   listed, marked "not available yet" and cannot be started.
4. **Given** the window closes, **Then** every connector process is stopped.
5. **Given** a dummy or replay connector running, **Then** the window shows that its crossings are
   test data.

---

### User Story 6 - How many chips worked (Priority: P3)

After the race the judge writes a chip report from the raw reads file and the start protocol: for
each bib, each of its chips, in how many of the bib's crossings it was read and how often; chips
never read; unknown chips.

**Why this priority**: It tells which chips and antenna positions to fix before the next race, but
nothing at the race depends on it.

**Independent Test**: With the reads of Story 1, the report says chip A of bib 15 was read in 2 of
2 crossings and chip B in 1 of 2.

**Acceptance Scenarios**:

1. **Given** raw reads and a start protocol, **When** the judge writes the report, **Then** a text
   file next to the results file lists the above.

### Edge Cases

- Two reads of two bibs at the same moment: each bib gets its own crossing.
- A read that arrives late with an earlier time (a reader flushing its buffer after a reconnect):
  it joins the pass its time falls into; a pass that never had a crossing gets one, and a crossing
  already written is not moved. The new crossing is appended after newer lines:
  FinishProtocolGenerator finds laps by time, not by line order.
- The dead time changed mid-race: it applies to reads from then on.
- A chip in the start protocol in lower case, with stray punctuation or with spaces inside (an EPC
  typed in groups of four): matched the way StartProtocolMaker normalises chip ids.
- A start protocol line without a bib or with `NOT_PAID`: its chips are not bound.
- A relay of three stages with bib 21 and chips `A1;B1;C1`: A1 binds to 21, B1 to 22, C1 to 23.
- The results file was edited while chip reads keep coming: crossings still append after the
  edited content.
- The results file cannot be written (a removed folder, a full disk) while chips run: crossings
  wait in the retry queue and reach the file once it can be written; nothing pops up.
- A beam break whose shift cannot write the oldest slot: the slots stay as they are, the break is
  in the raw beam file and the failure is in the action log, without a dialog.
- A connector floods the chronometer: reads are handled in order without freezing the interface.
- The chip source is stopped: reads stop; the dead-time state is kept, so a restart within the
  dead time does not double a crossing.
- The program restarts during a race: the source stays stopped until the judge presses Start; reads
  a reader buffered meanwhile arrive late and are handled by FR-009.
- The judge chooses another results file: the raw files and the chip state of the new file are
  used from then on, starting empty for a new file; those of the old file stay as they are.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The judge chooses the event source: by hand (always on), beam, chips. Beam and chips
  each run one connector chosen from a list; the choice and the connector settings are saved with
  the event's settings. A connector starts only when the judge presses Start, also after the
  program restarts: nothing is run on its own, a custom command least of all.
- **FR-002**: A connector is a separate process that reports events as lines on its output and
  takes commands as lines on its input, under one documented protocol. Events carry what readers
  report: chip id, time on the host clock if the connector knows it, the device's own time,
  antenna, signal strength, reader id; a beam break carries its time and a sequence number. The
  protocol is shared with ChronometerAndroid.
- **FR-003**: Connectors shipped: dummy chips, dummy beam, replay (a raw reads file played back),
  custom command; stubs, listed and not startable: LLRP (Impinj, Zebra), RaceResult decoder, R2000
  serial/TCP readers, USB beam, Bluetooth beam. While a dummy or replay connector runs, the window
  says that its crossings are test data, so a rehearsal is not uploaded as a race unnoticed.
- **FR-004**: A connector that exits or stops answering is restarted after 1 s, doubling to at most
  30 s while it keeps failing and back to 1 s once it has run for 30 s without failing; its state is
  shown; events are never handled on a thread that can block the interface.
- **FR-005**: A read's or a break's time is the host time the connector reports or, without one,
  the time the chronometer received it, in the results file's time format and with the summer-time
  setting.
- **FR-006**: Every chip read is appended to a raw reads file next to the results file,
  `chip#time#device time#antenna#signal#reader#`, before it is processed. A read whose line cannot
  be written is still processed, and the failure is logged.
- **FR-007**: The chip map is built from field 0 (bib) and field 11 (chip ids) of the start
  protocol file. Field 11 is split on commas and semicolons; each id there, and each id a reader
  reports, is compared upper case with everything but ASCII letters and digits dropped, as
  StartProtocolMaker normalises it. Semicolons separate the riders of a team: on a line with N > 1
  stages (field 4) and a numeric bib, the k-th rider (from 0) binds to bib + k -- the way
  FinishProtocolGenerator and the site number stage riders -- and riders past the N-th bind
  nothing; any other line binds every chip to its bib. A chip on two bibs is reported and not
  mapped. Lines without a bib, with `NOT_PAID` or with fewer than 12 `#` separators bind nothing.
- **FR-008**: "Download start protocol" fetches the site's start list with the site URL and token,
  only when pressed. On success it saves the previous file as a backup, writes the new one and
  rebuilds the map; on failure nothing changes and the judge sees why. A list with no lines is a
  failure ("nothing uploaded yet"), so a press before StartProtocolMaker uploaded cannot wipe a good
  file.
- **FR-009**: A bib's chip reads are grouped into passes by their read times, whatever order they
  arrive in: reads less than the dead time apart are one pass. A pass that has never had a crossing
  gets one as soon as it forms, timed at its first read. A crossing already written is never moved,
  even when a late read turns out earlier, and a pass that once had a crossing never gets another,
  even after the judge edits or deletes that crossing. Dead time: 5 s by default, settable from 1 s
  to 120 s; a change applies to reads from then on.
- **FR-010**: Reads of unknown chips are listed with first read, last read and count. When the map
  changes, the reads of chips that became known join their bib's reads; every pass of the bib (by
  FR-009) that has never had a crossing gets one, at its first read, appended. A crossing already
  written is never moved or removed by this; a chip that moves from one bib to another keeps its
  past crossings on the old bib.
- **FR-011**: Chip crossings are written like saved slots: appended to the results file, logged,
  uploaded with the debounce. A write a source causes never opens a dialog: a chip crossing that
  cannot be written waits in a queue shown in the Chips tab and counted on the source's state line,
  is kept with the chip state, and is retried every second until it is written; the failure is in
  the action log.
- **FR-012**: A beam break stamps the first slot without a time with the break's time and the
  current action, like the second-user FINISH button. When all slots are stamped, the slots shift as
  with that button, except that slot 5 gets the break's time with an empty number: the Next field
  is the judge's typing, and a machine event never takes it. Every break is appended to a raw beam
  file next to the results file, `sequence#time#device time#`.
- **FR-013**: The crossings list shows the results file. The judge can add a crossing (number,
  time, action; time defaults to now), edit one's number, time or action, and delete one after a
  confirmation.
- **FR-014**: Before a change the current results file is copied to a backup; if the copy fails,
  the change is refused. The new content replaces the file in one step, so a crash leaves the old
  or the new file, never a mix. The change is then uploaded as a snapshot.
- **FR-015**: Crossing counts next to the slots are counted from the results file and the slots,
  no longer from the action log, which an edit or a deletion does not change.
- **FR-016**: Closing the window stops every connector process.
- **FR-017**: "Chip report" writes the report of Story 6 to a text file next to the results file.

### Key Entities

- **Connector**: a program speaking the connector protocol; has a kind (chips or beam), settings
  and a state.
- **Chip read**: chip id, time, device time, antenna, signal strength, reader.
- **Pass**: a bib's reads less than the dead time apart; remembers whether it has had a crossing.
- **Beam break**: sequence number, time, device time.
- **Chip map**: chip id to bib, built from the start protocol file; with conflicts and unknowns.
- **Crossing**: a `number#time#action#` line of the results file.
- **Raw reads file / raw beam file**: append-only logs of everything a device reported.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The replay of a recorded read sequence produces exactly the expected crossings, at the
  times of the first reads, proven by unit tests on the read-to-crossing logic.
- **SC-002**: Killing a connector process while it is active loses no crossing it had already
  reported and does not freeze the window, proven by a Qt-level test.
- **SC-003**: Every change to the results file leaves a backup with the previous content, proven by
  tests that delete, add and edit.
- **SC-004**: With no source running, hand timing behaves as `specs/app/chronometer.md` describes,
  changed by this feature in one point only: crossing counts follow the results file (FR-015).
  Proven by the existing tests; only those that count from the action log change.
- **SC-005**: Nothing reaches the site without a button press or a results change; nothing is
  downloaded on start-up.

## Assumptions

- StartProtocolMaker writes chip ids into field 11 (its specification 002); a start protocol
  without field 11 binds no chip.
- The site's `GET /api/v1/start-list/` returns every device's uploaded lines; no site change is
  needed.
- Device clocks are mapped to the host clock inside a connector when a real device arrives; the
  dummy connectors use the host clock.
- The raw files are for the judge and for later analysis; they are not uploaded.
