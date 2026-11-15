"""The beam kit's enclosures, built in Blender: run through Blender's MCP bridge, or
headless with ``blender -b -P beam/enclosures/beam_enclosures.py``.

Every part is made in its print orientation, in millimetres (one Blender unit each),
and exported to stl/ beside this file; the scene is saved as beam_enclosures.blend.
PETG parts are grey in the viewport, TPU ones orange. README.md says how to print and
assemble them. Another lens changes LENS_D, LENS_EDGE and FOCAL below; nothing else.

The receiver is a tube: the lens in its front, sealed between two TPU gaskets by a
screwed ring; the light sensor on a carriage at the lens's focus, slid to it and then
fixed; the board behind it; a back cap with a TPU gasket, the USB cable through a TPU
grommet and a window for the board's LED. A collar clamps the tube and takes a
camera tripod's 1/4-20 screw in a captive nut. The emitter is a small box: the KY-008
laser through a TPU ring in its front, its USB cable through a TPU grommet, a lid on a
TPU gasket, the same tripod nut beneath.
"""

import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix

# -- the lens (a 3x hand magnifier's, taken out of its frame) --------------------
LENS_D = 60.0  # its diameter
LENS_EDGE = 2.5  # its thickness at the rim
FOCAL = 100.0  # from the lens to the sensor, about
# -- the rest -----------------------------------------------------------------------
FIT = 0.3  # clearance of a sliding or pressed fit
WALL = 3.0
GASKET = 1.0  # a lens gasket's thickness (TPU)
SEAL = 1.5  # a lid or cap gasket's thickness (TPU)
APERTURE = LENS_D - 4.0  # the shoulder the lens rests on leaves this open
FLANGE_T = 6.0  # an M3 screw's grip
SCREW_PILOT = 2.8  # an M3 screw cuts its own thread in PETG
SCREW_CLEAR = 3.4
FOCUS_RANGE = 20.0  # the carriage's travel around FOCAL, as lenses differ
BAY = 45.0  # behind the carriage: the board (and the BT05)
CARRIAGE_T = 8.0
MODULE_SLOT = (14.6, 9.5)  # the LM393 module, its trimmer too, through the carriage
NUT_AF, NUT_T, BOLT_D = 11.5, 6.0, 6.8  # a 1/4-20 nut (11.1 across flats), its bolt
CABLE_SLOT = (13.0, 8.0)  # a USB-C plug passes; the grommet then holds the cable
CABLE_D = 4.0
LED_WINDOW_D = 5.0
LASER_D = 6.4  # the KY-008's brass barrel
SEGMENTS = 128

TUBE_ID = LENS_D + 2 * FIT
TUBE_OD = TUBE_ID + 2 * WALL
FLANGE_OD = TUBE_OD + 16.0
SCREW_R = (TUBE_OD / 2 + FLANGE_OD / 2) / 2
SEAT = LENS_EDGE + 2 * GASKET - 0.5  # the lens stack pressed by half a millimetre
SHOULDER = 3.0
TUBE_LEN = SEAT + SHOULDER + FOCAL + FOCUS_RANGE + BAY
EMITTER_IN = (40.0, 26.0, 20.0)  # the emitter box inside: along the beam, across, up
EMITTER_WALL = 2.4

PETG, TPU = (0.62, 0.64, 0.66, 1.0), (0.95, 0.45, 0.1, 1.0)


def here():
    """This script's folder: its file when sent through the MCP bridge or run with
    blender -b -P; in the Text Editor, the file its text was opened from."""
    path = globals().get("__file__", "")
    if not Path(path).is_absolute():
        texts = [t for t in bpy.data.texts if t.filepath.endswith("beam_enclosures.py")]
        path = bpy.path.abspath(texts[0].filepath) if texts else path
    return Path(path).parent


OUT = here()


def new_object(name, bm):
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def cylinder(name, r, h, z=0.0, x=0.0, y=0.0, segments=SEGMENTS, rot=None):
    """A cylinder on the Z axis from z to z + h, at (x, y); ``rot`` turns it."""
    bm = bmesh.new()
    bmesh.ops.create_cone(
        bm, cap_ends=True, segments=segments, radius1=r, radius2=r, depth=h
    )
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, h / 2))
    if rot is not None:
        axis, angle = rot
        bmesh.ops.rotate(
            bm,
            verts=bm.verts,
            cent=(0, 0, 0),
            matrix=Matrix.Rotation(angle, 3, axis),
        )
    bmesh.ops.translate(bm, verts=bm.verts, vec=(x, y, z))
    return new_object(name, bm)


def box(name, sx, sy, sz, x=0.0, y=0.0, z=0.0):
    """A box sx by sy by sz, centred on (x, y) in plan, from z up."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(x, y, z + sz / 2))
    return new_object(name, bm)


def moved(obj, x, y, z):
    """An object's mesh moved, in the mesh itself: a cutter's place is its mesh's."""
    obj.data.transform(Matrix.Translation((x, y, z)))
    return obj


def hexagon(name, af, h, z=0.0, x=0.0, y=0.0, rot=None):
    return cylinder(name, af / math.sqrt(3), h, z, x, y, segments=6, rot=rot)


def boolean(target, others, operation):
    """``target`` with ``others`` cut away or joined; the others are removed."""
    for other in others:
        mod = target.modifiers.new("boolean", "BOOLEAN")
        mod.operation = operation
        mod.object = other
        mod.solver = "EXACT"
        other.hide_set(True)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    baked = bpy.data.meshes.new_from_object(target.evaluated_get(depsgraph))
    old = target.data
    target.modifiers.clear()
    target.data = baked
    bpy.data.meshes.remove(old)
    for other in others:
        mesh = other.data
        bpy.data.objects.remove(other)
        bpy.data.meshes.remove(mesh)
    return target


def cut(target, *others):
    return boolean(target, others, "DIFFERENCE")


def join(target, *others):
    return boolean(target, others, "UNION")


def screw_holes(name, r, d, h, z, count=3, start=90.0):
    """Holes of diameter ``d`` on a circle of radius ``r``, through h from z."""
    holes = []
    for i in range(count):
        angle = math.radians(start + i * 360.0 / count)
        x, y = r * math.cos(angle), r * math.sin(angle)
        holes.append(cylinder(f"{name}{i}", d / 2, h, z, x, y, segments=32))
    return holes


def ring(name, outer_d, inner_d, h, z=0.0):
    return cut(
        cylinder(name, outer_d / 2, h, z),
        cylinder(name + "_hole", inner_d / 2, h + 2, z - 1),
    )


def receiver_tube():
    """Printed standing on its back flange, the lens end up."""
    body = cylinder("receiver_tube", TUBE_OD / 2, TUBE_LEN)
    back = cylinder("back_flange", FLANGE_OD / 2, FLANGE_T)
    front = cylinder("front_flange", FLANGE_OD / 2, FLANGE_T, TUBE_LEN - FLANGE_T)
    join(body, back, front)
    bore = cylinder("bore", TUBE_ID / 2, TUBE_LEN - SEAT - SHOULDER + 1, -1)
    shoulder_z = TUBE_LEN - SEAT - SHOULDER
    aperture = cylinder("aperture", APERTURE / 2, SHOULDER + 2, shoulder_z - 1)
    seat = cylinder("seat", TUBE_ID / 2, SEAT + 1, TUBE_LEN - SEAT)
    pilots = screw_holes("back_pilot", SCREW_R, SCREW_PILOT, 10, -1)
    pilots += screw_holes("front_pilot", SCREW_R, SCREW_PILOT, 10, TUBE_LEN - 9)
    return cut(body, bore, aperture, seat, *pilots)


def lens_ring():
    """Presses the lens and its gaskets onto the shoulder; printed flat."""
    part = ring("receiver_lens_ring", FLANGE_OD, APERTURE, 3.0)
    return cut(part, *screw_holes("ring_hole", SCREW_R, SCREW_CLEAR, 5, -1))


def back_cap():
    """Closes the tube's back: its plug in the bore, its flange on the gasket."""
    cap = cylinder("receiver_back_cap", FLANGE_OD / 2, FLANGE_T)
    plug = cylinder("plug", TUBE_ID / 2 - FIT, 6.0, FLANGE_T)
    join(cap, plug)
    hollow = cylinder("hollow", TUBE_ID / 2 - FIT - 2.4, 7.0, FLANGE_T - 1.0 + 1.2)
    cable = box("cable", CABLE_SLOT[0], CABLE_SLOT[1], 20, x=12.0, z=-5)
    led = cylinder("led", LED_WINDOW_D / 2, 20, -5, x=-12.0, segments=32)
    holes = screw_holes("cap_hole", SCREW_R, SCREW_CLEAR, 10, -1)
    return cut(cap, hollow, cable, led, *holes)


def sensor_carriage():
    """Slides in the bore to the focus, the LM393 module through it, then is fixed."""
    disc = cylinder("receiver_sensor_carriage", TUBE_ID / 2 - FIT, CARRIAGE_T)
    slot = box("module_slot", MODULE_SLOT[0], MODULE_SLOT[1], CARRIAGE_T + 2, z=-1)
    return cut(disc, slot)


def duplicate(obj, name):
    """A second object of the same shape, its mesh its own."""
    copy = obj.copy()
    copy.data = obj.data.copy()
    copy.name = copy.data.name = name
    bpy.context.scene.collection.objects.link(copy)
    return copy


def tripod_collar():
    """Two halves clamping the tube between its flanges, which no whole ring would
    pass; a 1/4-20 nut in the lower one's foot takes a camera tripod. Printed with
    their axis up: the nut, its bolt and the two clamp screws lie across."""
    width, inner = 20.0, TUBE_OD + FIT
    outer = inner + 8.0
    ear_x = outer / 2 + 4.0  # the clamp screws, either side of the tube
    whole = cylinder("tripod_collar", outer / 2, width)
    foot = box("foot", 30.0, 16.0, width, y=-(outer / 2 + 2.0))
    ears = [box(f"ear{s}", 10.0, 12.0, width, x=s * ear_x) for s in (-1, 1)]
    join(whole, foot, *ears)
    bore = cylinder("collar_bore", inner / 2, width + 2, -1)
    sole = -(outer / 2 + 10.0)  # the foot's face on the tripod
    across = ((1, 0, 0), math.radians(90))  # a cylinder's axis turned onto -Y
    nut = hexagon("nut", NUT_AF, NUT_T + 1, -1, rot=across)
    moved(nut, 0, sole + NUT_T - 1, width / 2)  # 1 mm out of the face: a clean cut
    bolt = moved(cylinder("bolt", BOLT_D / 2, 14, rot=across), 0, sole + 12, width / 2)
    screws = [
        moved(cylinder(f"clamp{s}", SCREW_CLEAR / 2, 20, rot=across), s * ear_x, 10, 10)
        for s in (-1, 1)
    ]
    cut(whole, bore, nut, bolt, *screws)
    # Split across the axis, 0.4 mm apart: tightened, the halves close on the tube.
    top = duplicate(whole, "tripod_collar_top")
    cut(top, box("below", 200.0, 200.0, width + 2, y=-100.0 + 0.2, z=-1))
    whole.name = whole.data.name = "tripod_collar_bottom"
    cut(whole, box("above", 200.0, 200.0, width + 2, y=100.0 - 0.2, z=-1))
    return [top, whole]


def emitter_box():
    """The KY-008 laser inside, its barrel through the front; printed on its floor."""
    w = EMITTER_WALL
    lx, ly, lz = EMITTER_IN
    shell = box("emitter_box", lx + 2 * w, ly + 2 * w, lz + w)
    inside = box("inside", lx, ly, lz + 1, z=w)
    pad = NUT_T + 2.5  # a ledge under the board: the tripod nut's pocket closed above
    ledge_x = lx / 2 - 10.0  # the ledge's middle: the board on it against the front
    beam_z = pad + 1.6 + LASER_D / 2  # the barrel's axis: on its board, on the pad
    along = ((0, 1, 0), math.radians(90))  # a cylinder's axis turned onto +X
    barrel = moved(cylinder("barrel", 4.7, 10, rot=along), lx / 2 - 2, 0, beam_z)
    cable = box("emitter_cable", 8.0, CABLE_SLOT[0], CABLE_SLOT[1], x=-lx / 2 - 2)
    moved(cable, 0, 0, beam_z - CABLE_SLOT[1] / 2)
    nut = hexagon("emitter_nut", NUT_AF, NUT_T + 1, -1, x=ledge_x)
    bolt = cylinder("emitter_bolt", BOLT_D / 2, w + 6, -1, x=ledge_x, segments=48)
    cut(shell, inside)  # hollowed first: the bosses and the pad then stand inside
    bosses = [
        cylinder(f"boss{i}", 3.5, lz, w, x, y, segments=32)
        for i, (x, y) in enumerate(corners(lx, ly))
    ]
    ledge = box("ledge", 20.5, ly + 1.0, pad, x=ledge_x + 0.25)  # into the walls
    join(shell, *bosses, ledge)
    pilots = [
        cylinder(f"pilot{i}", SCREW_PILOT / 2, 12, w + lz - 11, x, y, segments=24)
        for i, (x, y) in enumerate(corners(lx, ly))
    ]
    return cut(shell, barrel, cable, nut, bolt, *pilots)


def corners(lx, ly):
    """The lid screws' bosses: 3.5 mm round, half a millimetre into the walls, so they
    join them instead of touching them along a line."""
    inset = 3.0
    return [
        (sx * (lx / 2 - inset), sy * (ly / 2 - inset))
        for sx in (-1, 1)
        for sy in (-1, 1)
    ]


def emitter_lid():
    w = EMITTER_WALL
    lx, ly, _ = EMITTER_IN
    lid = box("emitter_lid", lx + 2 * w, ly + 2 * w, 2.4)
    holes = [
        cylinder(f"lid_hole{i}", SCREW_CLEAR / 2, 5, -1, x, y, segments=24)
        for i, (x, y) in enumerate(corners(lx, ly))
    ]
    return cut(lid, *holes)


def tpu_parts():
    """The soft parts: two lens gaskets, the back cap's and the lid's gaskets, the
    cable grommet (two: receiver and emitter) and the laser's ring."""
    lens = ring("tpu_lens_gasket", TUBE_ID - FIT, APERTURE, GASKET)
    cap = ring("tpu_back_cap_gasket", FLANGE_OD, TUBE_ID + 0.5, SEAL)
    cut(cap, *screw_holes("gasket_hole", SCREW_R, SCREW_CLEAR, 4, -1))
    w = EMITTER_WALL
    lx, ly, _ = EMITTER_IN
    lid = box("tpu_emitter_lid_gasket", lx + 2 * w, ly + 2 * w, SEAL)
    inner = box("lid_gasket_inner", lx, ly, SEAL + 2, z=-1)
    holes = [
        cylinder(f"lid_gasket_hole{i}", SCREW_CLEAR / 2, 4, -1, x, y, segments=24)
        for i, (x, y) in enumerate(corners(lx, ly))
    ]
    cut(lid, inner, *holes)
    grommet = box("tpu_cable_grommet", CABLE_SLOT[0] + 4, CABLE_SLOT[1] + 4, 2.0)
    plug = box("grommet_plug", CABLE_SLOT[0] + 0.4, CABLE_SLOT[1] + 0.4, 5.0, z=2.0)
    join(grommet, plug)
    hole = cylinder("grommet_hole", CABLE_D / 2, 10, -1, segments=32)
    slit = box("grommet_slit", 0.6, CABLE_SLOT[1] + 6, 10, y=CABLE_SLOT[1] / 2, z=-1)
    cut(grommet, hole, slit)
    laser = ring("tpu_laser_ring", 9.6, LASER_D - 0.6, 3.0)
    return [lens, cap, lid, grommet, laser]


def window():
    """A window for the operators that want one: the MCP bridge runs outside any."""
    windows = bpy.context.window_manager.windows
    return {"window": windows[0], "screen": windows[0].screen} if windows else {}


def preview(parts):
    """preview.png: every part in a row, as printed, for the README."""
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "OBJECT"
    scene.render.resolution_x, scene.render.resolution_y = 2000, 640
    scene.render.film_transparent = True  # on a light page or a dark one
    left = min(o.location.x - o.dimensions.x / 2 for o in parts)
    right = max(o.location.x + o.dimensions.x / 2 for o in parts)
    camera = bpy.data.cameras.new("preview")
    camera.type, camera.ortho_scale = "ORTHO", (right - left) * 1.04
    camera.clip_end = 10_000.0
    eye = bpy.data.objects.new("preview", camera)
    bpy.context.scene.collection.objects.link(eye)
    eye.location = ((left + right) / 2, -600.0, 420.0)
    eye.rotation_euler = (math.radians(58), 0.0, 0.0)
    scene.camera = eye
    scene.render.filepath = str(OUT / "preview.png")
    with bpy.context.temp_override(**window()):
        bpy.ops.render.render(write_still=True)


def fresh_scene():
    """An empty scene. Sent through the bridge, a new file; run in the Text Editor,
    whose text a new file would take away, the same file emptied."""
    if Path(globals().get("__file__", "")).is_absolute():
        bpy.ops.wm.read_homefile(use_empty=True)
        return
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj)


def build():
    fresh_scene()
    units = bpy.context.scene.unit_settings
    units.system, units.scale_length, units.length_unit = "METRIC", 0.001, "MILLIMETERS"
    petg = [
        receiver_tube(),
        lens_ring(),
        back_cap(),
        sensor_carriage(),
        *tripod_collar(),
        emitter_box(),
        emitter_lid(),
    ]
    tpu = tpu_parts()
    stl = OUT / "stl"
    stl.mkdir(parents=True, exist_ok=True)
    x = 0.0
    for obj in petg + tpu:
        obj.color = TPU if obj in tpu else PETG
        width = obj.dimensions.x
        obj.location.x = x + width / 2
        x += width + 15.0
        for other in bpy.context.scene.objects:
            other.select_set(False)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        with bpy.context.temp_override(**window()):
            bpy.ops.wm.stl_export(
                filepath=str(stl / f"{obj.name}.stl"),
                export_selected_objects=True,
                global_scale=1.0,
                use_scene_unit=False,
                apply_modifiers=True,
                ascii_format=False,
            )
    preview(petg + tpu)
    with bpy.context.temp_override(**window()):
        blend = OUT / "beam_enclosures.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(blend), compress=True)
    return {obj.name: [round(v, 1) for v in obj.dimensions] for obj in petg + tpu}


parts = build()
if "result" in globals():  # run through the MCP bridge: say what was made
    globals()["result"].update(parts)
