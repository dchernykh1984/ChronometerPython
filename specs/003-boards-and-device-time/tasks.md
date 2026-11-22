# Tasks: The boards around, and a clock that knows world time

**Input**: [spec.md](spec.md), [plan.md](plan.md). Desktop tasks in this repository; Android's in
ChronometerAndroid's PR, which keeps to the same spec.

## Desktop (ChronometerPython)

- [x] T001 `app/device_time.py`: SNTP of several servers, the best answers, the offset and how far it
  may be off (plan, decision 5); the device clock, never running backwards (decision 7); tests
- [x] T002 The device clock in the window: a round at start and every 64 s on a thread; every stamp
  on it, a connector's event corrected as it arrives; the clock line and the action log (decisions
  8, 9); Qt-level tests
- [x] T003 `beam-boards`: several boards at once, a bridge each, every break out, the states summed,
  a `blink` command; a HELLO of either kind taken (decision 1); tests
- [x] T004 `beam-scan` and `beam-blink` (decisions 2, 3); tests
- [x] T005 The source box: Beam boards, the test beam, the custom command in that order; the list of
  boards with Find and Blink, the pick kept; an old single-board pick carried over (decisions 1, 4);
  Qt-level tests
- [x] T006 The connector protocol's `found` message and `blink` command
  (`specs/001-event-sources/contracts/connector-protocol.md`); the frozen builds' smoke test on
  `beam-boards`; README, `beam/README.md`, CLAUDE.md and AGENTS.md

## Android (ChronometerAndroid)

- [ ] T007 The device clock: SNTP, GNSS with its plausibility (decision 6), the best source, never
  backwards; every stamp on it; tests
- [ ] T008 The boards' finder and Blink; one Beam boards source reading several boards; the list
  first in the devices, then the test sources; the pick kept, the old name carried over; tests
- [ ] T009 The location asked as timing starts; the service's location type; the clock line;
  README

## Both

- [ ] T010 20 review cycles on each PR (20 more if they do not converge), then the releases
- [ ] T011 Field check (SC-001): two devices, two beams cut at once, 20 times over an hour
