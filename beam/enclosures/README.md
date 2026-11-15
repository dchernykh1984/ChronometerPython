# The beam's enclosures (first version)

![Every part as printed: PETG grey, TPU orange](preview.png)

Made in Blender 5.2 by `beam_enclosures.py`. `stl/` has one print file per part, already
in its print orientation, in millimetres. `beam_enclosures.blend` keeps the same parts for
editing. This is a first version: it has not been printed yet. It is to be tried, and then
changed (spec 002, FR-013 and FR-016).

## The parts

| File | Material | Count | What it is |
| --- | --- | --- | --- |
| `receiver_tube.stl` | PETG | 1 | The receiver's body: the lens at its top end, the sensor and the board inside. |
| `receiver_lens_ring.stl` | PETG | 1 | Presses the lens and its two gaskets into the tube; 3 screws. |
| `receiver_sensor_carriage.stl` | PETG | 1 | Holds the light sensor module at the lens's focus. |
| `receiver_back_cap.stl` | PETG | 1 | Closes the tube: a slot for the USB cable, a window for the board's LED. |
| `tripod_collar.stl` | PETG | 1 | Clamps the tube and takes a camera tripod's screw. |
| `emitter_box.stl` | PETG | 1 | The laser's box: the barrel through its front, a tripod nut underneath. |
| `emitter_lid.stl` | PETG | 1 | Closes the laser's box; 4 screws. |
| `tpu_lens_gasket.stl` | TPU | 2 | One on each side of the lens. |
| `tpu_back_cap_gasket.stl` | TPU | 1 | Between the tube and its back cap. |
| `tpu_emitter_lid_gasket.stl` | TPU | 1 | Between the laser's box and its lid. |
| `tpu_cable_grommet.stl` | TPU | 2 | Seals a USB cable's slot: one in the back cap, one in the laser's box. Slit to take the cable. |
| `tpu_laser_ring.stl` | TPU | 1 | Seals the laser's barrel in the box's front hole. |

## Printing

- **PETG.** 0.2 mm layers, 4 walls, 5 top and bottom layers, 25 to 40% infill, no supports.
  Print the receiver in black or another dark colour, so that no daylight comes through
  its walls. The tube stands on its back flange: the shoulder the lens rests on is a 2.3 mm
  overhang, which PETG prints.
- **TPU** (95A). 0.2 mm layers, 100% infill, slow (20 to 30 mm/s), no retraction worth
  speaking of.
- Every part lies on the print bed as exported.

## What else to buy

| Part | Count | Where it goes |
| --- | --- | --- |
| A 3x hand magnifier, 60 mm glass lens | 1 | Its lens, out of its frame, into the tube (see "The lens" below). |
| M3 x 10 screw | 6 | The lens ring and the back cap (they cut their thread in PETG). |
| M3 x 8 screw | 4 | The emitter's lid. |
| M3 x 20 screw and an M3 nut | 1 | The collar's clamp. |
| 1/4-20 hex nut (camera thread) | 2 | Pressed into the collar's foot and under the emitter's box. |
| A camera tripod with a pan and tilt head | 2 | One for the receiver, one for the emitter: aiming them. |

## The lens

The receiver is made for a 60 mm lens that focuses about 100 mm behind itself. A 3x hand
magnifier's lens is about that. Over 10 m, a lens catches the laser's spot anywhere on its
face and focuses it onto the sensor, so the spot may wander up to 2.5 cm without the beam
being lost. A bare sensor loses it after 3 mm (spec 002, FR-009, FR-012).

To find a lens's focal length, focus the sun, or a lamp across the room, onto a sheet of
paper: the distance from the lens to the sharpest spot is its focal length. Another lens
changes three numbers at the top of `beam_enclosures.py`: `LENS_D` (its diameter),
`LENS_EDGE` (its thickness at the rim) and `FOCAL`. Then build the parts again (below).

## Assembly

1. **Lens.** Lay a lens gasket on the shoulder at the tube's top, then the lens, then the
   second gasket. Put the lens ring on top and fix it with 3 M3 x 10 screws, tightened
   evenly until the gaskets are pressed.
2. **Sensor.** Push the light sensor module through the carriage's slot, its photoresistor
   forward. Slide the carriage into the tube from the back, the photoresistor towards the
   lens.
3. **Focus.** Aim the laser at the lens from 10 m away. Slide the carriage until the
   sensor's LED is lit most steadily. Fix the carriage there with a drop of hot glue.
4. **Board.** Wire the board to the sensor as `beam/README.md` says. Fix the board, and the
   BT05 in the RP2040 kit, behind the carriage with foam tape.
5. **Back cap.** Pass the USB cable through the cap's slot, plug it in, and close the slot
   with a cable grommet around the cable. Fix the cap on its gasket with 3 M3 x 10 screws.
   The board's LED shows through the cap's window. Seal the window with a drop of clear
   epoxy, or a disc of clear plastic.
6. **Collar.** Press a 1/4-20 nut into the collar's foot, slide the collar onto the tube at
   its middle, and clamp it with the M3 x 20 screw and its nut. Put it on a tripod.
7. **Emitter.** Press a 1/4-20 nut into the box's bottom. Lay the KY-008 on the ledge
   inside, its barrel through the TPU ring in the front hole. Bring the USB cable in
   through a grommet in the back: its +5 V to the laser's `S` pin, its ground to its `-`
   pin. A cut USB cable or a USB-C breakout board does. Put the lid on its gasket with 4
   M3 x 8 screws. Put it on the second tripod.

## Sealing

These parts are sealed by their gaskets and grommets, and can be opened again. The way the
kit is sealed for good is chosen once they have been tried (spec 002, FR-013). The options
are potting the electronics in a compound, which this tube leaves room for, a conformal
coating, or these gaskets.

## Building the parts again

The script makes every part, writes `stl/`, `preview.png` and `beam_enclosures.blend`
beside itself, and says the parts' sizes. Run it in any of these ways:

- **Through Blender's MCP add-on** (Blender Lab's, on `localhost:9876`): send it as one
  request, with `__file__` set to its path. This is how these files were made.
- **In Blender's Text Editor:** open the script, then Run Script.
- **Headless:** `blender -b -P beam/enclosures/beam_enclosures.py`.

Each way gives the same parts.
