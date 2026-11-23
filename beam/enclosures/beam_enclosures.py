"""The beam kit's enclosures, built in Blender: run through Blender's MCP bridge, or
headless with ``blender -b -P beam/enclosures/beam_enclosures.py``.

Every part is made in its print orientation, in millimetres (one Blender unit each),
and exported to stl/ beside this file; the scene is saved as beam_enclosures.blend.
README.md says how to print and assemble them. Another lens changes LENS_D, LENS_EDGE
and FOCAL below; nothing else.

Six parts, all PETG, sealed with neutral silicone: no gaskets, two screws. The
receiver is a tube: the lens dropped in from its back onto a shoulder at its front;
the light sensor on a carriage at the lens's focus, slid to it and then fixed; the
board behind it; a back cap on two screws, with a slot for the USB cable and a window
for the board's LED. A hood slides over the tube's front, and a boss under the tube
takes a camera tripod's 1/4-20 screw in a nut slid into it. The emitter is a box: the
KY-008 laser on a ledge, its barrel through the front, its USB-C power module behind
it, the cable through the back, a lid; the tripod's nut slides into the ledge.
"""

import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

# -- the lens (a 3x hand magnifier's, taken out of its frame) --------------------
LENS_D = 60.0  # its diameter
LENS_EDGE = 2.5  # its thickness at the rim
FOCAL = 100.0  # from the lens to the sensor, about
# -- the rest -----------------------------------------------------------------------
FIT = 0.3  # clearance of a sliding fit
WALL = 3.0
APERTURE = LENS_D - 4.0  # the shoulder the lens rests on leaves this open
SHOULDER = 3.0  # the tube's front, the lens against it from behind
HOOD = 100.0  # how far the hood reaches in front of the tube
HOOD_OVER = 15.0  # how far it slides over the tube
HOOD_WALL = 2.4
HOOD_STOP = 2.0  # the tube's front rim the hood's lip stops on
FOCUS_RANGE = 20.0  # the carriage's travel around FOCAL, as lenses differ
BAY = 45.0  # behind the carriage: the board (and the BT05)
CARRIAGE_T = 8.0
MODULE_SLOT = (14.6, 9.5)  # the LM393 module, its trimmer too, through the carriage
CAP_T = 3.0  # the back cap's disc
PLUG = 8.0  # its plug in the bore, which the two screws hold
PLUG_WALL = 4.0  # an M3 screw's grip
SCREW_PILOT = 2.8  # an M3 screw cuts its own thread in PETG
SCREW_CLEAR = 3.4
NUT_AF, NUT_T, BOLT_D = 11.5, 6.0, 6.8  # a 1/4-20 nut (11.1 across flats), its bolt
NUT_FLOOR = 1.5  # under the nut: a tripod's short screw still reaches through it
SCREW_ROOM = 3.0  # past the nut, for a screw longer than its floor and the nut
BOSS = (24.0, 40.0)  # the tripod boss's face: across the tube, along it
BOSS_DEPTH = 11.0  # from the tube's outside to the face
BOSS_Z = 55.0  # its middle from the tube's front: the receiver's balance, about
CABLE_SLOT = (13.0, 8.0)  # a USB-C plug passes; silicone then fills round the cable
LED_WINDOW_D = 5.0
LASER_D = 6.4  # the KY-008's brass barrel
# The first layers come out squashed wider: an edge on the bed that slides into
# another part is chamfered by this much.
FLARE = 0.6
SEGMENTS = 128

TUBE_ID = LENS_D + 2 * FIT
TUBE_OD = TUBE_ID + 2 * WALL
TUBE_LEN = SHOULDER + LENS_EDGE + 1.0 + FOCAL + FOCUS_RANGE + BAY
BOSS_FACE = -(TUBE_OD / 2 + BOSS_DEPTH)  # the boss's face, under the tube (-Y)
EMITTER_IN = (60.0, 26.0, 22.0)  # the emitter box inside: along the beam, across, up
EMITTER_WALL = 2.4
LEDGE = 21.0  # the laser's board on it, against the front

# Print the receiver black, the emitter in any colour: so shown in the preview.
RECEIVER, EMITTER = (0.22, 0.22, 0.24, 1.0), (0.62, 0.64, 0.66, 1.0)


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


def cylinder(name, r, h, z=0.0, x=0.0, y=0.0, segments=SEGMENTS, rot=None, r2=None):
    """A cylinder on the Z axis from z to z + h, at (x, y), its top of radius r2 if
    given (a cone); ``rot`` turns it before it is moved."""
    bm = bmesh.new()
    bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        segments=segments,
        radius1=r,
        radius2=r if r2 is None else r2,
        depth=h,
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


def hull(name, points):
    """The convex hull of ``points``: a boss with its slope, or a nut's slot."""
    bm = bmesh.new()
    for point in points:
        bm.verts.new(point)
    made = bmesh.ops.convex_hull(bm, input=bm.verts[:])
    inside = made["geom_interior"] + made["geom_unused"]  # may name a vertex twice
    drop = {g for g in inside if isinstance(g, bmesh.types.BMVert)}
    bmesh.ops.delete(bm, geom=list(drop), context="VERTS")
    # One face per side, not a fan of thin triangles: a cut through a thin one leaves
    # an edge of no length, and the print file a hole.
    bmesh.ops.dissolve_limit(
        bm, angle_limit=math.radians(0.1), verts=bm.verts[:], edges=bm.edges[:]
    )
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return new_object(name, bm)


def bed_chamfer(name, r):
    """A cutter taking FLARE off, at 45 degrees, the edge on the bed of a part of
    radius r."""
    around = cylinder(name, r + 1, FLARE + 1, -1)
    keep = cylinder(name + "_keep", r - FLARE - 1, FLARE + 1, -1, r2=r)
    return cut(around, keep)


def hexagon(across, turn=0.0):
    """A nut's outline: six corners, ``across`` its flats, turned by ``turn`` degrees
    from a corner on the first axis."""
    r = across / math.sqrt(3)
    angles = [math.radians(turn + 60 * i) for i in range(6)]
    return [(r * math.cos(a), r * math.sin(a)) for a in angles]


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


ALONG_X = ((0, 1, 0), math.radians(90))  # a cylinder's axis turned onto +X
ALONG_MINUS_Y = ((1, 0, 0), math.radians(90))  # onto -Y


def receiver_tube():
    """Printed standing on its front, the shoulder on the bed; the boss beneath the
    tube slopes at 45 degrees towards the bed, so it needs no support."""
    tube = cylinder("receiver_tube", TUBE_OD / 2, TUBE_LEN)
    join(tube, tripod_boss())
    bore = cylinder("bore", TUBE_ID / 2, TUBE_LEN - SHOULDER + 1, SHOULDER)
    aperture = cylinder("aperture", APERTURE / 2, SHOULDER + 2, -1)
    screws = cylinder(  # the back cap's two screws, either side, through the walls
        "cap_screws",
        SCREW_CLEAR / 2,
        TUBE_OD + 2,
        TUBE_LEN - PLUG / 2,
        x=-(TUBE_OD / 2 + 1),
        segments=32,
        rot=ALONG_X,
    )
    flare = bed_chamfer("front_chamfer", TUBE_OD / 2)  # the hood slides over it
    return cut(tube, bore, aperture, screws, flare, *boss_holes())


def tripod_boss():
    """Under the tube (-Y): a flat face for the tripod, sloped beneath. It reaches into
    the bore, which is cut after it, so it joins the curved wall all along."""
    face, inner = BOSS_FACE, -(TUBE_ID / 2 - 2.0)
    low, high = BOSS_Z - BOSS[1] / 2, BOSS_Z + BOSS[1] / 2
    corners = [(face, low), (face, high), (inner, high), (inner, low - (inner - face))]
    return hull(
        "tripod_boss",
        [(x, y, z) for x in (-BOSS[0] / 2, BOSS[0] / 2) for y, z in corners],
    )


def boss_holes():
    """The 1/4-20 nut's slot, open at the boss's top (towards the tube's back), and
    its bolt's hole from the face: the nut held by plastic between it and the tripod,
    so a tightened screw pulls it onto the boss, never out of it."""
    near, far = BOSS_FACE + NUT_FLOOR, BOSS_FACE + NUT_FLOOR + NUT_T
    top = BOSS_Z + BOSS[1] / 2 + NUT_AF
    nut = hexagon(NUT_AF, turn=30.0)  # its flats along the slot
    slot = hull(
        "nut_slot",
        [(x, y, z + dz) for x, dz in nut for y in (near, far) for z in (BOSS_Z, top)],
    )
    bolt_len = far + SCREW_ROOM - (BOSS_FACE - 1)
    bolt = cylinder(
        "bolt",
        BOLT_D / 2,
        bolt_len,
        BOSS_Z,
        y=far + SCREW_ROOM,
        segments=48,
        rot=ALONG_MINUS_Y,
    )
    return [slot, bolt]


def receiver_hood():
    """Slides over the tube's front until its lip meets the tube's front rim. Printed
    standing on its own front, the lip's underside a 45-degree slope."""
    bore = TUBE_OD + 2 * FIT
    lip = TUBE_OD - 2 * HOOD_STOP
    slope = (bore - lip) / 2
    hood = cylinder("receiver_hood", bore / 2 + HOOD_WALL, HOOD + HOOD_OVER)
    # 0.2 mm into the slope: two cutters never share a face, and the step is too
    # small to print as an overhang.
    ahead = cylinder("ahead", bore / 2, 1 + HOOD - slope + 0.2, -1)
    under = cylinder("lip_slope", bore / 2, slope, HOOD - slope, r2=lip / 2)
    through = cylinder("lip_hole", lip / 2, slope + 2, HOOD - slope - 1)
    over = cylinder("over", bore / 2, HOOD_OVER + 1, HOOD)
    return cut(hood, ahead, under, through, over)


def back_cap():
    """Closes the tube's back: its plug in the bore on two screws, its disc on a bead
    of silicone. Printed on its disc."""
    cap = cylinder("receiver_back_cap", TUBE_OD / 2, CAP_T)
    plug = cylinder("plug", TUBE_ID / 2 - FIT, PLUG, CAP_T)
    join(cap, plug)
    hollow = cylinder("hollow", TUBE_ID / 2 - FIT - PLUG_WALL, PLUG + 1, CAP_T)
    cable = box("cable", CABLE_SLOT[0], CABLE_SLOT[1], 20, x=12.0, z=-5)
    led = cylinder("led", LED_WINDOW_D / 2, 20, -5, x=-12.0, segments=32)
    pilots = cylinder(
        "pilots",
        SCREW_PILOT / 2,
        TUBE_ID + 2,
        CAP_T + PLUG / 2,
        x=-(TUBE_ID / 2 + 1),
        segments=24,
        rot=ALONG_X,
    )
    return cut(cap, hollow, cable, led, pilots)


def sensor_carriage():
    """Slides in the bore to the focus, the LM393 module through it, then is fixed."""
    disc = cylinder("receiver_sensor_carriage", TUBE_ID / 2 - FIT, CARRIAGE_T)
    slot = box("module_slot", MODULE_SLOT[0], MODULE_SLOT[1], CARRIAGE_T + 2, z=-1)
    return cut(disc, slot, bed_chamfer("carriage_chamfer", TUBE_ID / 2 - FIT))


def emitter_box():
    """The KY-008 laser on a ledge, its barrel through the front, the power module
    behind it; printed on its floor. The tripod's nut slides into the ledge from
    behind, the floor between it and the tripod."""
    w = EMITTER_WALL
    lx, ly, lz = EMITTER_IN
    shell = box("emitter_box", lx + 2 * w, ly + 2 * w, lz + w)
    inside = box("inside", lx, ly, lz + 1, z=w)
    cut(shell, inside)  # hollowed first: the ledge then stands inside
    ledge_top = NUT_FLOOR + NUT_T + SCREW_ROOM + 1.0
    # Half a millimetre into the walls and the floor: joined, not touching them.
    ledge = box(
        "ledge",
        LEDGE + 0.5,
        ly + 1.0,
        ledge_top - w + 0.5,
        x=lx / 2 - LEDGE / 2 + 0.25,
        z=w - 0.5,
    )
    join(shell, ledge)
    nut_x = lx / 2 - LEDGE / 2
    exit_x = lx / 2 - LEDGE - NUT_AF  # out of the ledge's back, into the box
    slot = hull(
        "emitter_nut_slot",
        [
            (x + dx, dy, z)
            for dx, dy in hexagon(NUT_AF)  # its flats along the slot
            for x in (nut_x, exit_x)
            for z in (NUT_FLOOR, NUT_FLOOR + NUT_T)
        ],
    )
    bolt = cylinder(
        "emitter_bolt",
        BOLT_D / 2,
        NUT_FLOOR + NUT_T + SCREW_ROOM + 1,
        -1,
        x=nut_x,
        segments=48,
    )
    beam_z = ledge_top + 1.6 + LASER_D / 2  # the barrel's axis: on its board
    barrel = cylinder(
        "barrel", LASER_D / 2, w + 2, beam_z, x=lx / 2 - 1, segments=48, rot=ALONG_X
    )
    cable = box(
        "emitter_cable",
        w + 2,
        CABLE_SLOT[0],
        CABLE_SLOT[1],
        x=-lx / 2 - w / 2,
        z=w + 1.0,
    )
    return cut(shell, slot, bolt, barrel, cable)


def emitter_lid():
    """Pressed onto the box on a bead of silicone, its rim inside the box's walls;
    printed on its face."""
    w = EMITTER_WALL
    lx, ly, _ = EMITTER_IN
    lid = box("emitter_lid", lx + 2 * w, ly + 2 * w, 2.4)
    rim = box("lid_rim", lx - 2 * FIT, ly - 2 * FIT, 3.0, z=2.4)
    join(lid, rim)
    inner = box("rim_inside", lx - 2 * FIT - 3.2, ly - 2 * FIT - 3.2, 4.0, z=2.4)
    return cut(lid, inner)


def window():
    """A window for the operators that want one: the MCP bridge runs outside any."""
    windows = bpy.context.window_manager.windows
    return {"window": windows[0], "screen": windows[0].screen} if windows else {}


def preview(parts):
    """preview.png: every part in a row, as printed, for the README; the camera
    framed on the parts' corners, the tallest as well as the widest row."""
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "OBJECT"
    scene.render.resolution_x, scene.render.resolution_y = 2000, 800
    scene.render.film_transparent = True  # on a light page or a dark one
    tilt = math.radians(58)
    up = (math.cos(tilt), math.sin(tilt))  # the camera's up, in Y and Z
    ahead = (math.sin(tilt), -math.cos(tilt))  # where it looks, in Y and Z
    bpy.context.view_layer.update()
    corners = [o.matrix_world @ Vector(c) for o in parts for c in o.bound_box]
    xs = [c.x for c in corners]
    us = [c.y * up[0] + c.z * up[1] for c in corners]
    mid_x, mid_u = (min(xs) + max(xs)) / 2, (min(us) + max(us)) / 2
    aspect = scene.render.resolution_x / scene.render.resolution_y
    camera = bpy.data.cameras.new("preview")
    camera.type = "ORTHO"
    camera.ortho_scale = max(max(xs) - min(xs), (max(us) - min(us)) * aspect) * 1.06
    camera.clip_end = 10_000.0
    eye = bpy.data.objects.new("preview", camera)
    bpy.context.scene.collection.objects.link(eye)
    back = 1000.0
    eye.location = (
        mid_x,
        mid_u * up[0] - back * ahead[0],
        mid_u * up[1] - back * ahead[1],
    )
    eye.rotation_euler = (tilt, 0.0, 0.0)
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
    receiver = [receiver_tube(), receiver_hood(), sensor_carriage(), back_cap()]
    emitter = [emitter_box(), emitter_lid()]
    parts = receiver + emitter
    stl = OUT / "stl"
    stl.mkdir(parents=True, exist_ok=True)
    for old in stl.glob("*.stl"):  # a part that is gone leaves no file to print
        old.unlink()
    for obj in parts:  # each where it was made: a print file moves with no other
        obj.color = RECEIVER if obj in receiver else EMITTER
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
    x = 0.0
    for obj in parts:  # then in a row, for the preview and the .blend
        obj.location.x = x + obj.dimensions.x / 2
        x += obj.dimensions.x + 15.0
    preview(parts)
    with bpy.context.temp_override(**window()):
        blend = OUT / "beam_enclosures.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(blend), compress=True)
    return {obj.name: [round(v, 1) for v in obj.dimensions] for obj in parts}


parts = build()
if "result" in globals():  # run through the MCP bridge: say what was made
    globals()["result"].update(parts)
