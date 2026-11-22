# Feature Specification: A beam ready for real races

**Feature Branch**: `002-field-ready-beam`

**Created**: 2026-11-15

**Status**: Draft

**Input**: User description: "The laser beam made ready for real races. The time of a break is taken
on the board's own chip, so no Bluetooth delay moves it; the beam works over a USB cable and over
Bluetooth, on the desktop and on the phone; it rides out a laser wavering in the wind (a lens?);
the emitter and the receiver are sealed against the weather (epoxy?); 3D models of the enclosures
are designed; the repository keeps each kind of thing in a folder of its own next to the code
(models apart, firmware for each chip apart). Plus what was decided before about the beam."

## Context

The RP2040 beam board works today over a USB cable: on the desktop chronometer (v0.5.0, device
"Beam board RP2040 (USB)") and on the Android app (v0.9.0, "USB beam"). It times each break with its
own clock, and both apps read it by one contract, `specs/001-event-sources/contracts/
beam-board-protocol.md`. A judge's finger over its sensor stamps cutoffs in both apps. What it is
not yet is a beam for a real race: it needs a cable to the laptop or phone, a bare sensor that a
wavering laser misses, and no protection from rain. Spec 001 already asks for a beam that rides out
the wind (FR-019, SC-007, research 11, task T023); this spec takes that over with the rest.

## Clarifications

### Session 2026-11-22

- Q: What accuracy can the beam promise, a start and a finish together? -> A: A hundredth of a
  second, never a thousandth. On the prototype a break's time is off by about half a
  millisecond as a rule, 9 in 10 within 1.8 ms over Bluetooth and 2.5 ms at most over USB, so
  a start's and a finish's errors together stay well under 10 ms. Results are given in
  hundredths; the chronometer still keeps milliseconds in its files, as data. The light
  sensor's own delay, the same at both ends when both are beams, is measured by the falling
  weight (SC-010).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The board's own time, whatever the link (Priority: P1)

A rider crosses the beam; the judge's laptop or phone may get the news late -- over Bluetooth some
10 to 50 ms late, and not the same each time -- but the break's time is the moment the board saw
it, by the board's own clock. The judge sees the same time for the same crossing whether the board
is on a cable or on Bluetooth.

**Why this priority**: A timing that depends on the link is no timing: Bluetooth would add tens of
milliseconds of noise to every rider, more than separates riders at a sprint finish.

**Independent Test**: Break the beam 200 times with a reference timer watching the same light, once
over the cable and once over Bluetooth; each break's time is compared with the reference.

**Acceptance Scenarios**:

1. **Given** a board on Bluetooth, **When** a rider crosses, **Then** the break's time is the board's
   first edge mapped onto the host's clock, within 2 ms of the reference, however late its message
   came.
2. **Given** the same crossing seen by one board over the cable and the same board over Bluetooth,
   **When** both times are compared, **Then** they differ by no more than 2 ms.
3. **Given** a break whose message reaches the host before the board's clock is mapped, **When**
   the mapping comes, **Then** the break is timed by the board's clock, never by when its message
   arrived over Bluetooth.

---

### User Story 2 - The beam over a cable or over Bluetooth, on the desktop and on the phone (Priority: P1)

The judge chooses how the board is linked: a USB cable, as now, or Bluetooth, with no cable across
the finish. Both the desktop chronometer and the Android app offer both. A board on Bluetooth runs
on its own power for a whole race day and keeps timing when the link drops: what it saw meanwhile
reaches the judge once the link is back.

**Why this priority**: A cable across a finish line is a trip hazard and ties the judge to the
line; the wired version stays for whoever has it, and as the fallback.

**Independent Test**: Run a race of breaks through a board on Bluetooth to the desktop and to the
phone; cut the link for a minute mid-race; every break arrives, each with its right time.

**Acceptance Scenarios**:

1. **Given** the desktop chronometer or the Android app, **When** the judge chooses the beam device,
   **Then** each board is offered on each of its links -- the RP2040-Zero over USB or through its
   HM-10 over Bluetooth, the ESP32-C3 over USB or over Bluetooth -- and the choice is kept.
2. **Given** several boards in Bluetooth range (a start and a finish, say), **When** the judge picks
   one, **Then** it is picked by a name or id the board shows, and the app never reads another.
3. **Given** a board on Bluetooth whose link drops for 60 s, **When** the link is back, **Then**
   every break it saw meanwhile reaches the app, each with its board time, and the app says that
   the link was down and for how long.
4. **Given** a board on its own power, **When** its power runs low, **Then** the app tells the judge
   well before it runs out.

---

### User Story 3 - A beam that rides out the wind (Priority: P2)

At 10 m a tilt of 0.06 degrees moves a laser's spot by 1 cm, more than a bare sensor is wide: the
wind on a stand, or a metal ramp flexing under riders, would break the beam at every gust. The
field-ready beam reports no break when only the beam wavers, and still sees every rider.

**Why this priority**: Without it the beam fails its first windy race; it needs the board of
Story 1 to be tested with.

**Independent Test**: Spec 001's SC-007, at 10 m: shake the stands for 5 minutes, the spot moving
up to 2 cm, and sweep a hand through the beam 50 times.

**Acceptance Scenarios**:

1. **Given** the beam set up at 10 m, **When** its stands are shaken so that the spot moves up to
   2 cm, **Then** no break is reported.
2. **Given** the same beam, **When** a hand or a wheel at 60 km/h crosses it, **Then** a break is
   reported every time.
3. **Given** the sun low in the receiver's view, **When** a rider crosses, **Then** the break is seen
   and the sun alone makes none.

---

### User Story 4 - An emitter and a receiver that stand the weather (Priority: P2)

Races go on in rain, dust and morning dew. The emitter and the receiver are sealed against them,
and still let the beam through a clear window, let the judge aim them, and let the battery be
charged and the firmware be updated without breaking the seal.

**Why this priority**: One wet race would end a board that is not sealed; a sealed one that cannot
be charged or updated is no better.

**Independent Test**: Spray each part with water from every side for 10 minutes, leave it out over
a night, then time a race of breaks with it.

**Acceptance Scenarios**:

1. **Given** a sealed emitter and receiver, **When** they are sprayed from every side for 10
   minutes, **Then** no water is inside and the beam works after.
2. **Given** rain on the parts during a race, **When** a rider crosses, **Then** the break is seen,
   and drops on the window make no break of their own.
3. **Given** a sealed board, **When** its battery is low or its firmware is to be updated, **Then**
   both can be done without opening or breaking the seal.

---

### User Story 5 - Enclosures and mounts anyone can print (Priority: P3)

Every part has an enclosure and a mount designed for a hobby 3D printer: the emitter, the receiver,
the board with its battery, and a stand or a stake mount that keeps the beam off a flexing ramp,
with a way to aim. The models are in the repository, as editable sources and as files ready to
print.

**Why this priority**: The parts need a body to be used at a race at all; printing them makes the
kit cheap and repeatable.

**Independent Test**: Print every part from the repository's files with its stated settings, and
assemble a kit with them.

**Acceptance Scenarios**:

1. **Given** the repository alone, **When** someone prints every part with the settings stated,
   **Then** the parts fit the electronics and each other with no change.
2. **Given** a part to change, **When** it is opened from its source model, **Then** it can be
   edited and exported to a new print file.

---

### User Story 6 - Everything for a kit in its own folder (Priority: P3)

The repository keeps everything for the beam in one folder next to the code: a README for the kits
(what to buy and for how much, how to wire, flash and use them), the firmware with a subfolder for
each chip or board (the RP2040-Zero with its BT05, the ESP32-C3), and the enclosure models in a
subfolder of their own, each with its README and its versions pinned. One copy of the repository
is enough to build the whole kit, the same way every time.

**Why this priority**: The kit is built again by others and for other races; a scattered or
unpinned kit is built differently each time.

**Independent Test**: Someone new to the project builds a working kit from the repository alone.

**Acceptance Scenarios**:

1. **Given** the repository, **When** someone looks for a chip's firmware or a part's model, **Then**
   it is in that chip's or that part's folder, with a README that says how to build or print it.
2. **Given** two kits built from one version of the repository, **When** they are compared, **Then**
   they run the same firmware and have the same parts.

---

### Edge Cases

- The Bluetooth link drops while a rider crosses: the break is kept on the board and comes once the
  link is back, with its board time.
- The board restarts (power lost): its count and clock start anew; the app says so, as it does over
  USB today.
- Two boards in range, a start and a finish: each app reads only the board it was told to.
- The battery runs low mid-race: the judge is told well before the board stops.
- Rain on the optical window, condensation inside after a cold night: neither makes a break of its
  own nor hides a rider.
- The sun low in the receiver's view, or a reflection from a car: no break of its own.
- A sealed board must be re-flashed for a new firmware: it can be, without opening it.
- The judge aims the beam alone at 12 m: the board shows when the light reaches the receiver.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A break's time MUST be the moment of its first edge by the board's own clock, mapped
  onto the host's clock; no link delay, USB or Bluetooth, may move it.
- **FR-002**: The mapping of the board's clock onto the host's MUST stay within 2 ms of the truth
  over Bluetooth, although a round trip there takes 15 to 60 ms (the contract's 20 ms limit on
  round trips is for USB), and within 3 ms over USB: the most half its round trip allows, 2.0 to
  2.5 ms on the prototype read by a Mac, where the cable's and the radio's mappings agree within
  0.5 ms on average.
- **FR-003**: A break over Bluetooth MUST be stamped by the board's clock, never by when its
  message arrived, as long as the clock can be mapped: one that comes before the mapping waits
  for it. Only when no mapping comes within 10 s is it stamped by its arrival, rather than held
  and maybe lost, and the judge is told so.
- **FR-004**: The beam MUST work over a USB cable and over Bluetooth alike, on the desktop
  chronometer and on the Android app; the judge chooses the link, and the choice is kept.
- **FR-005**: The board MUST speak the same lines of the one contract over both links; anything new
  the Bluetooth link needs (a battery level, breaks kept while the link was down) is added to the
  contract first, for both apps and every board.
- **FR-006**: A board on Bluetooth MUST keep timing when its link drops, keep at least the last 100
  breaks it saw meanwhile, and send them with their board times once the link is back; the app
  says the link was down and for how long.
- **FR-007**: With several boards in range, the judge MUST pick a board by a name or id the board
  shows; an app MUST never read a board it was not told to.
- **FR-008**: A board on Bluetooth MUST run on its own power (a battery or a power bank) for at least
  10 hours, report its power level, and warn the judge when 20% is left.
- **FR-009**: The beam MUST report no break when only the beam wavers -- the spot moving up to 2 cm
  at 10 m -- and MUST report every crossing of a rider (spec 001, FR-019).
- **FR-010**: The receiver MUST NOT be blinded by the sun nor make breaks of its own from sunlight
  or reflections.
- **FR-011**: The beam MUST work with its parts 10 to 12 m apart.
- **FR-012**: The beam MUST ride out the wind by a lens: the laser's spot caught by a lens of 5 to
  7.5 cm, wide enough for FR-009's wavering, with the sensor at its focus in a black tube behind a
  red filter. An industrial retroreflective sensor was weighed and set aside: the ones that reach
  10 to 12 m cost several times FR-020's limit, and the ones within it reach 2 to 4 m.
- **FR-013**: The emitter and the receiver MUST be sealed against rain, dust and dew, as an IP65
  class at least, IP67 aimed, while keeping a clear optical window, a way to aim, and a way to charge
  and re-flash without breaking the seal. Sealing is required; the way (potting in a compound, a
  conformal coating, or a gasketed enclosure) is chosen once the first printed enclosures have been
  tried, and until then the enclosures leave room for any of them.
- **FR-014**: The board MUST help aiming: its light shows whether the beam reaches the receiver, and
  it tells the app the light's state, as `STATUS` does today.
- **FR-015**: On request the board MUST light a light the PhotoFinish cameras see at 10 m in
  daylight, and report the moment on its clock (the contract's `FLASH`), so a video frame can be tied
  to the board's clock (ChronometerPython#49, comment 5).
- **FR-016**: Every part MUST have a 3D-printable enclosure and mount -- the emitter, the receiver,
  the board with its battery, and a stand or a stake mount that keeps the beam off a ramp with a way
  to aim -- kept in the repository as editable source models, print-ready files, and the print
  settings: PETG, fit for sun and rain, with TPU for gaskets and other soft parts. The models are
  made in Blender.
- **FR-017**: The repository MUST keep everything for the beam in one folder next to the code: a
  README for the kits (what to buy with prices, how to wire, flash and use them), the firmware with
  a subfolder for each chip or board, and the enclosure models in a subfolder; each subfolder with
  its README and its versions pinned, so the whole kit is built the same way from the repository
  alone.
- **FR-018**: Bluetooth MUST come from two boards, both read by both apps, over Bluetooth and over
  the cable alike: an ESP32-C3 SuperMini, whose own chip has Bluetooth, and the RP2040-Zero with an
  HM-10 module wired to it (or a clone on the same CC2541 chip, such as the AT-09 or MLT-BT05). Each
  chip's firmware lives in its own folder (FR-017): a new one for the ESP32-C3, the RP2040's
  extended to drive the HM-10. Both boards are in the apps' device list.
- **FR-019**: The beam MUST keep the uses it has today: riders crossing one at a time (time trials,
  downhill), each break a rider's cutoff, and group starts; a crossing is never lost, and every
  break stays in the beam's raw file first.
- **FR-020**: The parts that make one beam -- the emitter, the receiver and their optics -- MUST
  cost no more than 10,000 tenge in all, bought in Kazakhstan; the rest of the kit is as cheap as
  it can be, and its README lists every part with its price and where it was bought.
- **FR-021**: Once a kit works at a race, an article MUST be published in the cycling site's
  knowledge base: what the beam is, what to buy, how to build, flash and set it up, and how both
  chronometers read it, pointing to the repository's beam folder.
- **FR-022**: The board's clock MUST be mapped anew at every PING's answer for as long as the
  link is up, never set once at the connection and kept. Set once, the mapping's own error (up
  to 2 ms over Bluetooth) would stay for the whole race, with the crystal's drift piling up on
  it; read all the time, it moves by about that much at most from one rider to the next, and a
  link that came back is read again by itself, with no question to the judge. The hypotheses
  this rests on MUST be checked on the prototype's first flashing, and on every board flashed
  over USB after it: the mapping within 3 ms over USB and 2 ms over Bluetooth (FR-002); its
  move from one answer to the next about 0.3 ms over USB (0.5 ms at most) and 0.5 ms over
  Bluetooth (3 ms at most); the board's crystal within 60 ppm of the computer's clock (the prototype's: about
  +46 and -41), and on the prototype
  how far that moves in the cold; and the way through the radio as long one way as the other,
  which the BT05's UART could make otherwise. A board outside any of them is looked at before
  it times a race.

### Key Entities *(include if feature involves data)*

- **Beam board**: a board the apps read; its name or id, firmware version, link (USB or Bluetooth),
  power level, and the breaks it keeps while its link is down.
- **Break**: a crossing as the board saw it -- its count, its time on the board's clock, its time on
  the host's clock.
- **Firmware variant**: the firmware for one chip or board; its version, its pinned build, its
  README.
- **Enclosure part**: one printed part; its source model, its print file, its print settings, the
  electronics it holds.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Over either link, 99% of 200 test breaks are within 2 ms of a reference timer watching
  the same light; one crossing over the cable and over Bluetooth differs by at most 2 ms.
- **SC-002**: With the Bluetooth link cut for 60 s mid-race and restored, every break seen meanwhile
  appears in the app with its right time; none is lost.
- **SC-003**: A board on its own power runs a 10-hour race day with its link up, and the judge is
  warned at 20% power left.
- **SC-004**: Spec 001's SC-007 at 10 m: 5 minutes of shaking the stands, the spot moving up to 2 cm,
  no break; 50 hand sweeps, 50 breaks.
- **SC-005**: With the sun low in the receiver's view for 10 minutes, no break of its own, and a hand
  sweep still seen every time.
- **SC-006**: After 10 minutes of water spray from every side and a night outdoors, no water is
  inside and the beam times a race of breaks with no miss.
- **SC-007**: One person aims the emitter and the receiver 12 m apart within 5 minutes.
- **SC-008**: A FLASH is seen on every camera at 10 m in daylight, tying a frame to the board's clock
  within one frame.
- **SC-009**: Someone new to the project builds a working kit -- firmware flashed, parts printed and
  assembled, wired -- from the repository alone, with no question asked.
- **SC-010**: Two kits, one beam 0.5 m under the other, time a weight dropped from rest above them:
  over 20 drops, the interval between their breaks matches free fall from the measured heights
  within 2 ms with both boards on the cable, within 4 ms with both on Bluetooth.
- **SC-011**: The site's knowledge base has the article of FR-021, and an organiser who reads it
  finds every part to buy and every step to build, flash and use a kit.
- **SC-012**: The clock check says every hypothesis of FR-022 within on both kits' first
  flashing, warm and after an hour in the cold, and on every board flashed after them.

## Assumptions

- Bluetooth means Bluetooth Low Energy carrying the contract's lines as a serial stream; the desktop
  runs on a computer with Bluetooth. The HM-10 has a serial service of its own (FFE0, characteristic
  FFE1), not the Nordic UART Service ChronometerPython#49 (comment 3) proposed: the plan settles
  whether the ESP32-C3's firmware offers the HM-10's service as well, so the apps read one, or the
  apps read both.
- The USB cable version stays as it is, the fallback and the choice of whoever has no Bluetooth.
- Parts are printed on a hobby FDM printer, in PETG, with TPU for soft parts.
- Two kits are built first, both on Bluetooth: the RP2040-Zero with a BT05 (an HM-10 clone on the
  CC2541) and an ESP32-C3 SuperMini, each with an LM393 light sensor on a photoresistor and a KY-008
  laser; the lenses are bought once one has been tried.
- The hardware choices are made in this PR; only the way of sealing waits, for the first printed
  enclosures (FR-013).
- Chips and video analysis are out of scope: their own specs cover them.
- This spec takes over spec 001's FR-019, SC-007 and task T023; once it is planned, 001 points
  here.
