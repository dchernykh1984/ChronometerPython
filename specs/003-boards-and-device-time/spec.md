# Feature Specification: The boards around, and a clock that knows world time

**Feature Branch**: `003-boards-and-device-time`

**Created**: 2026-11-22

**Status**: Draft

**Input**: User description: "Start and finish may be hundreds of metres or kilometres apart, read by
a phone and a laptop: a rider's time is the finish less the start, so the two devices must agree on
the time. Let each app keep its device's clock to world time itself, from every way it has: the
internet when it answers, GPS, and so on; GPS may be jammed at a start, so a time that is not
plausible is never taken. Keep the laser board as simple as it is: everything in software. And the
boards: the phone asks to type a board's name, which is wrong; show the boards around in a list,
pick one or several, data only from the picked ones, any break of any of them a cutoff; a Blink
button to tell which board is which. The test beam and the custom command stay, after the boards."

## Context

A rider's time is a finish less a start, and on a real course the two are read by two devices far
apart: a phone at the start, a laptop or a phone at the finish. Spec 002 maps a board's clock onto
its own device's within a millisecond or two; the device's clock itself is the system's, which the
system keeps to world time within tens of milliseconds on a laptop and up to hundreds on a phone.
Two devices then disagree by far more than a hundredth of a second, the accuracy spec 002 promises.

The boards are picked today by typing a name (the phone) or by choosing among four entries, two
chips by two links (the desktop). Both apps are independent of each other, and stay so; the laser
board stays as it is, firmware 0.4: everything here is software.

## Clarifications

### Session 2026-11-22

- Q: How is a board connected? -> A: Found in a list of the boards around, on Bluetooth and on USB,
  and picked there by the judge, one or several; data comes from the picked ones only. The system's
  own Bluetooth settings play no part: the boards use Bluetooth Low Energy with no pairing.
- Q: Several boards picked: are their breaks merged? -> A: No. Every break of every picked board is a
  cutoff of its own, whichever board it came from. Boards at different points are read by different
  devices, or by copies of the app.
- Q: How does the judge tell the boards apart? -> A: By their names, and by a Blink button that makes
  a board's LED blink.
- Q: The test beam and the custom command? -> A: They stay, listed after the boards found.
- Q: Which sources of world time? -> A: Every one the device has: GNSS on the phone (asking for the
  location is fine), NTP over the internet whenever it answers (there may be no internet at the
  start nor at the finish), the system's own time last. GNSS may be jammed or spoofed at a start: a
  GNSS time that is not plausible is never taken.
- Q: May a laptop take its time from a phone beside it? -> A: No: the two apps stay independent of
  each other.
- Q: Where is the finish read? -> A: Usually on a laptop, but a phone at the finish must work as well.
- Q: An ESP32-C3's one-colour LED is lit while the laser is on its sensor, so `FLASH` showed nothing
  there: change the board? -> A: Yes, the one change to the boards: `FLASH` puts a lit one-colour LED
  out for its 100 ms (firmware and contract 0.5), and Blink is seen with the laser aimed.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The boards around, picked from a list (Priority: P1)

The judge opens the beam source and sees the boards around, each with its name, its link (Bluetooth
or USB) and how strong its signal is. The judge picks one or several, and presses Blink on one to
see its LED blink and know which it is. The app reads the picked boards only, remembers them, and
takes them up again by itself whenever they are back in reach. The test beam and the custom
command are listed after the boards.

**Why this priority**: typing a board's name is where every judge stumbled first.

**Independent Test**: two boards powered beside the device: both are listed within 15 s, Blink
lights the one pressed and no other, and picking both gives breaks from both.

**Acceptance Scenarios**:

1. **Given** two boards on Bluetooth and one on USB, **When** the judge asks for the boards around,
   **Then** all three are listed within 15 s, each with its name, its link and its signal.
2. **Given** the list, **When** the judge presses Blink on one board, **Then** that board's LED
   blinks and no other's does.
3. **Given** two boards picked, **When** timing starts, **Then** both are read, and no other board in
   range is.
4. **Given** boards picked and the app started again, **When** the boards are on, **Then** the app
   reads them again with no new pick.
5. **Given** the beam source's list of devices, **When** it is shown, **Then** the boards found come
   first, the test beam and the custom command after them.

---

### User Story 2 - Every break of every board a cutoff (Priority: P1)

With several boards picked, a break of any of them is a cutoff, timed by that board's own clock:
nothing is merged or compared. A board lost does not stop the others, and the judge sees the state
of each.

**Why this priority**: two boards on one line keep a race timed when one fails or is knocked off
its aim.

**Independent Test**: two boards picked, a hand through one beam and then through the other: two
cutoffs, each with its board's time.

**Acceptance Scenarios**:

1. **Given** two boards picked, **When** a hand breaks each beam once, **Then** two cutoffs are
   recorded, each timed by its own board.
2. **Given** two boards picked, **When** one is switched off, **Then** the other's breaks still come,
   and the judge is told the first is lost and when it is back.

---

### User Story 3 - A clock that knows world time (Priority: P1)

The app measures how far its device's clock is from world time, from every source the device has,
and stamps every cutoff, by hand or by a board, on the corrected clock. The judge sees where the
time comes from and how far it may be off. Two devices far apart then agree within milliseconds.

**Why this priority**: a rider's time is a finish less a start from two devices; without it the
hundredth of a second the beam keeps is lost between them.

**Independent Test**: two devices, each reading one of two beams set side by side, the beams cut at
once with one ruler: the two cutoffs agree within SC-001.

**Acceptance Scenarios**:

1. **Given** a phone outdoors with GNSS, **When** the app runs, **Then** its clock is corrected by
   GNSS, and the judge sees GNSS and how far the clock may be off.
2. **Given** a device with the internet and no GNSS (a laptop), **When** the app runs, **Then** its
   clock is corrected by NTP, and the judge sees the internet and how far the clock may be off.
3. **Given** neither the internet nor GNSS, **When** the app runs, **Then** the system's time is
   used as it is, and the judge is told the clock is not checked.
4. **Given** a GNSS time that disagrees with NTP's by over a second, or jumps (jammed, spoofed),
   **When** it comes, **Then** it is not taken, and the judge is told so.
5. **Given** a correction under a second that moves while a race is timed, **When** the clock is
   read, **Then** it never runs backwards: a correction that would set it back is eased in.

### Edge Cases

- The internet comes and goes: the last correction stays, how far it may be off grows with the time
  since it was measured, and the judge sees it grow.
- NTP servers that disagree: the answers with the shortest round trips are taken; a server whose
  answer disagrees with the others by more than its round trip allows is not.
- No GNSS fix, indoors: GNSS is not used; the internet or the system's time is.
- The location refused on the phone: GNSS is not used, and the judge is told once.
- A board picked but out of reach: said, and looked for again.
- Two boards of one name: told apart by their addresses.
- A correction of more than a few seconds (the system's clock set wrong by hand): taken, and the
  judge is told, as the cutoffs before it were on the old clock.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Both apps MUST list the beam boards around when asked: those on Bluetooth (advertised as
  `beam-` and the end of their id, or offering the boards' serial service) and those on USB (by the
  boards' USB ids), each with its name, its link and its signal, within 15 s (a portable
  desktop build first unpacks the program that looks).
- **FR-002**: The judge MUST be able to pick one or several boards from the list; the app MUST read the
  picked ones only, never another board in range (spec 002, FR-007), remember the pick, and read
  them again by itself.
- **FR-003**: The list MUST offer Blink for a board: the app makes its LED blink (the boards'
  contract's `FLASH`, a few times over) for the judge to see which board it is.
- **FR-004**: Every break of every picked board MUST be a cutoff of its own, timed by its own board's
  clock; breaks MUST NOT be merged or compared.
- **FR-005**: A picked board's link lost MUST NOT stop the other picked boards; the judge MUST see each
  picked board's state.
- **FR-006**: In the beam source's list of devices, the boards found MUST come first, then the test
  beam and the custom command, then the rest.
- **FR-007**: Each app MUST measure its device clock's offset from world time from every source the
  device has: GNSS on the phone, NTP over the internet whenever it answers; with neither, it MUST use
  the system's time as it is. It MUST never set the system's clock.
- **FR-008**: Every cutoff, by hand, by a board or by any other source, MUST be stamped on the
  device's clock corrected by the measured offset. The results files MUST keep their format.
- **FR-009**: The judge MUST see the clock's source (GNSS, the internet, the system) and how far it may
  be off, and MUST be told when the source changes or the clock is not checked.
- **FR-010**: A GNSS time MUST be taken only when it is plausible: steady from one fix to the next
  (it moves as the device's own clock does, within a few milliseconds), and within 1 s of NTP's when
  NTP has answered within the hour, else within a minute of the device's own clock. Otherwise it
  MUST be dropped, and the judge told (GNSS jammed or spoofed).
- **FR-011**: NTP MUST be asked of several servers, several times, and the answers with the shortest
  round trips taken; an answer from a server that is not synchronised (stratum 0 or 16, the alarm
  set) MUST NOT be taken.
- **FR-012**: The corrected clock MUST never run backwards for a correction under a second: one that
  would set it back is eased in, the clock running slower until it is in, never stopped. The first
  correction is taken at once, and so is one of over a second either way (the system's clock set
  wrong by hand), the judge told that the cutoffs before it were on the old clock.
- **FR-013**: The apps MUST stay independent of each other: neither takes its time, nor anything
  else, from the other.
- **FR-014**: On the phone, the location MUST be asked for once, as timing mode starts; refused, GNSS
  is not used and the judge is told once.
- **FR-015**: Measuring the clock MUST NOT hold up timing: it runs beside it, and a source that does
  not answer only leaves the last correction in place.

### Key Entities *(include if feature involves data)*

- **Board found**: a board in the list: its name, its address (Bluetooth) or port (USB), its link,
  its signal, and its kind once it has said HELLO.
- **The pick**: the boards the judge picked, remembered by name and address or port.
- **Device clock**: the offset of the device's clock from world time, its source, how far it may be
  off, and when it was last measured.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Two devices, two beams side by side cut at once, 20 times over an hour: with GNSS on
  both, their cutoffs agree within 3 ms each time; with the internet on both, within 20 ms.
- **SC-002**: A judge finds and picks two boards, and has breaks from both, within a minute of
  opening the beam source.
- **SC-003**: A GNSS time over a second off NTP's (a spoofed one) is never taken, over 20 tries.
- **SC-004**: Over a race day of corrections under a second, the corrected clock never runs
  backwards.

## Assumptions

- The boards stay as they are, firmware 0.4, but for one change (clarifications): firmware 0.5's
  `FLASH` puts a lit one-colour LED out, for Blink to be seen with the laser aimed.
- NTP reaches public servers over UDP port 123; a network that blocks it leaves the system's time.
- A laptop has no GNSS; a phone has, and the phone app may ask for the location.
- Android 8 and later, macOS, Windows and Linux, as today.
