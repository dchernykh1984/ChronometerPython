"""The beam kit's enclosures with the electronics printed in, built in Blender: run
through Blender's MCP bridge, or headless with
``blender -b -P beam/enclosures-embedded/embedded_enclosures.py``.

Every part is made in its print orientation, in millimetres (one Blender unit each),
and exported to stl/ beside this file; the scene is saved as embedded_enclosures.blend,
the parts rendered as printed (preview.png) and cut open (section.png). README.md says
how to print them, where the printer pauses and what is laid in then. Another lens
changes LENS_D, LENS_EDGE and FOCAL below; other parts, the numbers under them.

Three parts, all PETG, no screws: the printer pauses, the electronics are laid in, and
the print closes over them. The receiver's body stands on its front: an open bore, a
45-degree cone narrowing to the photoresistor's window, the light sensor module's slot
behind it, and a bay for the board (and the BT05) that a 45-degree roof closes after
the pause. A hole beside the slot reaches the module's trimmer, a window shows the
board's LED, and a boss under the body takes a camera tripod's 1/4-20 screw in a nut
slid into it. The hood holds the lens on a shoulder and slides over the body's front:
sliding it focuses the lens on the sensor. The emitter is a box that its roof closes
over the KY-008 laser, its USB-C power module and the tripod's nut. Each USB cable is
plugged in before the pause, laid in a slot, and stays.
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
# -- what is laid in at the pauses: measure yours ---------------------------------
MODULE_SLOT = (9.5, 14.6)  # the LM393 module: through its parts, across its board
MODULE_DEPTH = 30.0  # how far it goes in, photoresistor first; its pins stay above
TRIMMER = (8.0, 22.0)  # where its trimmer can be, along it from its front end
BAY = (56.0, 28.0)  # the board, the BT05 and the wires: across, up to the pause
EMITTER_IN = (60.0, 26.0, 20.0)  # the laser's box inside: along the beam, across, up
LASER_D = 6.4  # the KY-008's brass barrel
LEDGE = 21.0  # the laser's board on it, against the front
# -- the rest -----------------------------------------------------------------------
LAYER = 0.2  # a pause falls between two layers of this height
FIT = 0.3  # clearance of a sliding fit
WALL = 3.0
APERTURE = LENS_D - 4.0  # the shoulder the lens rests on leaves this open
SHOULDER = 3.0
GAP = 1.0  # behind the lens's rim: the body's front stops there
HOOD = 100.0  # how far the hood reaches in front of the lens's shoulder
HOOD_WALL = 2.4
FOCUS_RANGE = 20.0  # the hood's travel on the body, as lenses differ
OVERLAP = 15.0  # the least of the body the hood holds, at the longest focus
WINDOW_D = 6.0  # the photoresistor (5 mm) looks through it
ROOF_TOP = 2.0  # above a roof's top
CABLE_SLOT = (6.0, 16.0)  # a cable laid in at the pause: its width, its depth
LED_WINDOW_D = 5.0
LED_Z = 10.0  # its middle over the bay's floor: a board stood on an edge, its LED there
TRIM_W = 8.0  # the trimmer's hole across: a trimmer up to 3 mm off the board's middle
NUT_AF, NUT_T, BOLT_D = 11.5, 6.0, 6.8  # a 1/4-20 nut (11.1 across flats), its bolt
NUT_FLOOR = 1.5  # under the nut: a tripod's short screw still reaches through it
SCREW_ROOM = 3.0  # past the nut, for a screw longer than its floor and the nut
BOSS = (24.0, 40.0)  # the tripod boss's face: across the body, along it
BOSS_DEPTH = 11.0  # from the body's outside to the face
EMITTER_WALL = 2.4
# The first layers come out squashed wider: an edge on the bed that slides into
# another part is chamfered by this much.
FLARE = 0.6
SEGMENTS = 128


def on_layer(z):
    """z raised to the top of a layer: where a pause can fall."""
    return round(math.ceil(round(z / LAYER, 6)) * LAYER, 3)


TUBE_ID = LENS_D + 2 * FIT
TUBE_OD = TUBE_ID + 2 * WALL
HOOD_BORE = TUBE_OD + 2 * FIT
HOOD_BACK = OVERLAP + FOCUS_RANGE  # the hood's bore behind the lens, over the body
# The window from the body's front: the hood pushed fully on puts it FOCAL less half
# FOCUS_RANGE behind the lens; pulled FOCUS_RANGE further off, FOCAL and half of it.
SENSOR_Z = FOCAL - FOCUS_RANGE / 2 - GAP
BAY_FLOOR = SENSOR_Z + MODULE_DEPTH
PAUSE = on_layer(BAY_FLOOR + BAY[1])  # the receiver's: the bay open, its roof to come
BODY_LEN = PAUSE + BAY[0] / 2 + ROOF_TOP
# The boss's slope reaches BOSS_DEPTH ahead of its face: all of it behind the hood.
BOSS_Z = HOOD_BACK + 1.0 + BOSS_DEPTH + BOSS[1] / 2  # its middle from the body's front
BOSS_FACE = -(TUBE_OD / 2 + BOSS_DEPTH)  # the boss's face, under the body (-Y)
EMITTER_PAUSE = on_layer(EMITTER_WALL + EMITTER_IN[2])
# Focused, a ruler from the hood's back edge to the body's back end reads the lens's
# focal length and this.
RULER = BODY_LEN - HOOD_BACK - GAP - SENSOR_Z

# Print the receiver black, the emitter light: so shown in preview.png. Cut open, in
# section.png, the receiver is lighter, so its inside shows.
RECEIVER, EMITTER = (0.22, 0.22, 0.24, 1.0), (0.62, 0.64, 0.66, 1.0)
OPENED = (0.45, 0.45, 0.48, 1.0)


def here():
    """This script's folder: its file when sent through the MCP bridge or run with
    blender -b -P; in the Text Editor, the file its text was opened from."""
    path = globals().get("__file__", "")
    if not Path(path).is_absolute():
        texts = [
            t for t in bpy.data.texts if t.filepath.endswith("embedded_enclosures.py")
        ]
        path = bpy.path.abspath(texts[0].filepath) if texts else path
    if not Path(path).is_absolute():
        # Never Blender's working folder: build() empties the stl/ it finds there.
        raise RuntimeError("open embedded_enclosures.py from its file, then run it")
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
    """The convex hull of ``points``: a bore with its cone, a bay with its roof."""
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


def circle(r, z, segments=SEGMENTS):
    """Points round the Z axis, for a hull."""
    angles = [2 * math.pi * i / segments for i in range(segments)]
    return [(r * math.cos(a), r * math.sin(a), z) for a in angles]


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
        remove(other)
    return target


def remove(obj):
    data = obj.data
    bpy.data.objects.remove(obj)
    if isinstance(data, bpy.types.Mesh):
        bpy.data.meshes.remove(data)
    elif isinstance(data, bpy.types.Camera):
        bpy.data.cameras.remove(data)


def cut(target, *others):
    return boolean(target, others, "DIFFERENCE")


def join(target, *others):
    return boolean(target, others, "UNION")


ALONG_X = ((0, 1, 0), math.radians(90))  # a cylinder's axis turned onto +X
ALONG_MINUS_Y = ((1, 0, 0), math.radians(90))  # onto -Y


def receiver_body():
    """Printed standing on its front. The bore, then a 45-degree cone narrowing to the
    photoresistor's window, the module's slot behind it, and the bay: open at the
    pause, then closed by a 45-degree cone of a roof. No support anywhere."""
    body = cylinder("receiver_body", TUBE_OD / 2, BODY_LEN)
    join(body, tripod_boss())
    cone_z = SENSOR_Z - (TUBE_ID - WINDOW_D) / 2  # where the bore starts to narrow
    # The cone's tip 0.5 mm into the slot: two cutters never share a face.
    light = hull(
        "light",
        circle(TUBE_ID / 2, -1.0)
        + circle(TUBE_ID / 2, cone_z)
        + circle(WINDOW_D / 2 - 0.5, SENSOR_Z + 0.5),
    )
    slot = box("module_slot", *MODULE_SLOT, MODULE_DEPTH + 1, z=SENSOR_Z)
    trim_x = MODULE_SLOT[0] / 2 - 0.5  # from the trimmer's face in the slot, outwards
    trimmer = box(
        "trimmer_hole",
        TUBE_OD / 2 + 1 - trim_x,
        TRIM_W,
        TRIMMER[1] - TRIMMER[0],
        x=(TUBE_OD / 2 + 1 + trim_x) / 2,
        z=SENSOR_Z + TRIMMER[0],
    )
    bay = hull(
        "bay",
        circle(BAY[0] / 2, BAY_FLOOR)
        + circle(BAY[0] / 2, PAUSE)
        + [(0.0, 0.0, PAUSE + BAY[0] / 2)],
    )
    led = cylinder(  # the board's LED, on the trimmer's side
        "led_window",
        LED_WINDOW_D / 2,
        TUBE_OD / 2 - BAY[0] / 2 + 2,
        BAY_FLOOR + LED_Z,
        x=BAY[0] / 2 - 1,
        segments=32,
        rot=ALONG_X,
    )
    cable_y = (TUBE_OD / 2 + 1, BAY[0] / 2 - 1)  # from outside into the bay, on -Y
    cable = box(
        "cable_slot",
        CABLE_SLOT[0],
        cable_y[0] - cable_y[1],
        CABLE_SLOT[1],
        y=-(cable_y[0] + cable_y[1]) / 2,
        z=PAUSE - CABLE_SLOT[1],
    )
    flare = bed_chamfer("front_chamfer", TUBE_OD / 2)  # the hood slides over it
    return cut(body, light, slot, trimmer, bay, led, cable, flare, *boss_holes())


def tripod_boss():
    """Under the body (-Y): a flat face for the tripod, sloped beneath. It reaches into
    the bore, which is cut after it, so it joins the curved wall all along."""
    face, inner = BOSS_FACE, -(TUBE_ID / 2 - 2.0)
    low, high = BOSS_Z - BOSS[1] / 2, BOSS_Z + BOSS[1] / 2
    corners = [(face, low), (face, high), (inner, high), (inner, low - (inner - face))]
    return hull(
        "tripod_boss",
        [(x, y, z) for x in (-BOSS[0] / 2, BOSS[0] / 2) for y, z in corners],
    )


def boss_holes():
    """The 1/4-20 nut's slot, open at the boss's top (towards the body's back), and
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
    """The lens on a shoulder, pushed in from the hood's back; the body's front slides
    in behind it, and how far focuses the lens. Printed standing on its own front, the
    shoulder's underside a 45-degree slope."""
    slope = (HOOD_BORE - APERTURE) / 2
    seat = HOOD + SHOULDER  # the lens rests on the shoulder here
    stop = seat + LENS_EDGE + GAP  # the body's front stops here
    hood = cylinder("receiver_hood", HOOD_BORE / 2 + HOOD_WALL, stop + HOOD_BACK)
    # 0.2 mm into the slope, the seat 1 mm into the bore behind it: two cutters never
    # share a face, and the step is too small to print as an overhang.
    ahead = cylinder("ahead", HOOD_BORE / 2, 1 + HOOD - slope + 0.2, -1)
    under = cylinder(
        "shoulder_slope", HOOD_BORE / 2, slope, HOOD - slope, r2=APERTURE / 2
    )
    through = cylinder("aperture", APERTURE / 2, SHOULDER + 2, HOOD - 1)
    lens = cylinder("lens_seat", TUBE_ID / 2, LENS_EDGE + GAP + 1, seat)
    over = cylinder("over", HOOD_BORE / 2, HOOD_BACK + 1, stop)
    return cut(hood, ahead, under, through, lens, over)


def emitter_box():
    """The KY-008 laser on a ledge, its barrel at a hole in the front, the power module
    behind it, all laid in at the pause; then a 45-degree roof closes the box. Printed
    on its floor. The tripod's nut slides into the ledge from behind at the pause too,
    the floor between it and the tripod."""
    w = EMITTER_WALL
    lx, ly, _ = EMITTER_IN
    ridge = EMITTER_PAUSE + ly / 2
    shell = box("emitter", lx + 2 * w, ly + 2 * w, ridge + ROOF_TOP)
    inside = hull(
        "inside",
        [
            (x, y, z)
            for x in (-lx / 2, lx / 2)
            for y in (-ly / 2, ly / 2)
            for z in (w, EMITTER_PAUSE)
        ]
        + [(x, 0.0, ridge) for x in (-lx / 2, lx / 2)],
    )
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
    cable = box(  # through the back wall, down from the pause
        "emitter_cable",
        w + 2,
        CABLE_SLOT[0],
        CABLE_SLOT[1],
        x=-lx / 2 - w / 2,
        z=EMITTER_PAUSE - CABLE_SLOT[1],
    )
    return cut(shell, slot, bolt, barrel, cable)


def opened(obj, quarter=False):
    """A copy of ``obj`` cut open for section.png: its half towards the camera (-Y)
    taken off; for the body, the quarter between its trimmer's side (+X) and its
    boss's (-Y), turned to face the camera."""
    copy = obj.copy()
    copy.data = obj.data.copy()
    copy.name = obj.name + "_opened"
    copy.color = OPENED if obj.color[0] < 0.5 else obj.color  # the black ones lit up
    bpy.context.scene.collection.objects.link(copy)
    big = 1000.0
    # 0.05 mm off the middle: the knife's face lies on none of the part's.
    x = big / 2 + 0.05 if quarter else 0.0
    knife = box(
        "knife",
        big * (1 if quarter else 2),
        big,
        big,
        x=x,
        y=-big / 2 - 0.05,
        z=-big / 2,
    )
    cut(copy, knife)
    if quarter:
        copy.rotation_euler.z = math.radians(-45)
    return copy


def window():
    """A window for the operators that want one: the MCP bridge runs outside any."""
    windows = bpy.context.window_manager.windows
    return {"window": windows[0], "screen": windows[0].screen} if windows else {}


def in_a_row(objs):
    """Side by side along X, 15 mm apart, as they are turned."""
    x = 0.0
    for obj in objs:
        bpy.context.view_layer.update()
        xs = [(obj.matrix_world @ Vector(c)).x for c in obj.bound_box]
        obj.location.x += x - min(xs)
        x += max(xs) - min(xs) + 15.0


def render(objs, name):
    """``name``: only ``objs``, in a row, for the README; the camera framed on their
    corners, the tallest as well as the widest row. Returns the camera."""
    for other in bpy.context.scene.objects:
        other.hide_render = other.type == "MESH" and other not in objs
    in_a_row(objs)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "OBJECT"
    scene.display.shading.show_cavity = True  # its edges and hollows drawn darker
    scene.display.shading.cavity_type = "BOTH"
    scene.render.resolution_x, scene.render.resolution_y = 2000, 800
    scene.render.film_transparent = True  # on a light page or a dark one
    tilt = math.radians(58)
    up = (math.cos(tilt), math.sin(tilt))  # the camera's up, in Y and Z
    ahead = (math.sin(tilt), -math.cos(tilt))  # where it looks, in Y and Z
    bpy.context.view_layer.update()
    corners = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    xs = [c.x for c in corners]
    us = [c.y * up[0] + c.z * up[1] for c in corners]
    mid_x, mid_u = (min(xs) + max(xs)) / 2, (min(us) + max(us)) / 2
    aspect = scene.render.resolution_x / scene.render.resolution_y
    camera = bpy.data.cameras.new(name)
    camera.type = "ORTHO"
    camera.ortho_scale = max(max(xs) - min(xs), (max(us) - min(us)) * aspect) * 1.06
    camera.clip_end = 10_000.0
    eye = bpy.data.objects.new(name, camera)
    bpy.context.scene.collection.objects.link(eye)
    back = 1000.0
    eye.location = (
        mid_x,
        mid_u * up[0] - back * ahead[0],
        mid_u * up[1] - back * ahead[1],
    )
    eye.rotation_euler = (tilt, 0.0, 0.0)
    scene.camera = eye
    scene.render.filepath = str(OUT / name)
    with bpy.context.temp_override(**window()):
        bpy.ops.render.render(write_still=True)
    return eye


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
    receiver = [receiver_body(), receiver_hood()]
    emitter = [emitter_box()]
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
    sections = [opened(parts[0], quarter=True), opened(parts[1]), opened(parts[2])]
    for obj in [*sections, render(sections, "section.png")]:
        remove(obj)
    render(parts, "preview.png")
    with bpy.context.temp_override(**window()):
        blend = OUT / "embedded_enclosures.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(blend), compress=True)
    made = {obj.name: [round(v, 1) for v in obj.dimensions] for obj in parts}
    made["pauses"] = {"receiver_body": PAUSE, "emitter": EMITTER_PAUSE}
    made["ruler"] = round(RULER, 1)
    return made


parts = build()
if "result" in globals():  # run through the MCP bridge: say what was made
    globals()["result"].update(parts)
