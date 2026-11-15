# Tasks: A beam ready for real races

**Input**: [spec.md](spec.md), [plan.md](plan.md)

## Phase 1: Layout and contract

- [x] T001 Move `firmware/beam_rp2040/` into `beam/firmware/rp2040/` and point every reference at it
- [x] T002 Contract 0.4 in `specs/001-event-sources/contracts/beam-board-protocol.md`: Bluetooth
  (FFE0/FFE1), `PONG <n> <got_us> <sent_us>`, `RESEND <seq>`, the ESP32-C3's ids, the answers to the
  asker (FR-005)

## Phase 2: Firmware (US1, US2)

- [x] T003 `beam/firmware/core/beam.py`: the break logic out of the RP2040's main, links, PONG with
  both moments and a random wait, RESEND from the last 128 breaks
- [x] T004 RP2040: USB and the BT05 on UART0, the BT05 named and moved to 115200 baud at start
- [x] T005 ESP32-C3: USB and Bluetooth of its own (FFE0/FFE1, advertised as `beam-<4 hex>`)
- [x] T006 Tests for the core and both mains in `tests/test_beam_firmware.py`

## Phase 3: Desktop (US1, US2)

- [x] T007 `protocol.py`: the 0.4 PONG, the Bluetooth clock (shortest trip each way), RESEND and
  counts taken once (FR-002, FR-003, FR-006)
- [x] T008 `ble.py`: the Bluetooth transport through `bleak`; the boards in the device list (FR-004,
  FR-007)
- [ ] T009 Builds: `bleak` in the portable apps, the macOS Bluetooth usage text, the smoke test

## Phase 4: Android (US2) - ChronometerAndroid, its own pull request

- [ ] T010 The 0.4 bridge: PONG, the Bluetooth clock, RESEND
- [ ] T011 The Bluetooth beam source, its permissions, the device in the settings; the ESP32-C3 on USB

## Phase 5: Enclosures and docs (US5, US6)

- [ ] T012 Blender (through its MCP bridge): receiver with the lens tube, emitter, board box, TPU
  gaskets, tripod mount; STL and the .blend; `beam/enclosures/README.md`
- [ ] T013 `beam/README.md`: the two kits, parts with prices, wiring, flashing, the apps, trouble
- [ ] T014 `CLAUDE.md` and `AGENTS.md`: the beam folder and its rules

## Later (needs the parts, or a decision)

- [ ] T015 Field test on the hardware: SC-001 (cable against Bluetooth), SC-010 (the falling weight);
  calibrate the BT05's lopsided trip if it shows
- [ ] T016 The power level (FR-008), once the power is chosen
- [ ] T017 An external LED for FLASH on the ESP32-C3 (FR-015)
- [ ] T018 The way of sealing (FR-013), after the first printed enclosures
- [ ] T019 The knowledge-base article on the site (FR-021), once a kit has worked at a race
