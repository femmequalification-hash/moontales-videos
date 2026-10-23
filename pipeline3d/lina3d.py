"""3D Lina + park, rendered with Blender Cycles (free).

Usage: python3 lina3d.py -- OUT.png LAYER POSE
  LAYER: bg (park only) | char (Lina only, transparent background)
  POSE:  idle | talk | blink | wave
"""
import math
import random
import sys
import time

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
out = args[0] if args else "/tmp/lina3d.png"
layer = args[1] if len(args) > 1 else "all"
pose = args[2] if len(args) > 2 else "idle"

bpy.ops.wm.read_factory_settings(use_empty=True)
S = bpy.context.scene


def srgb(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)


def mat(name, hexcol, rough=0.5, sss=0.0, coat=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*srgb(hexcol), 1)
    b.inputs["Roughness"].default_value = rough
    if sss:
        b.inputs["Subsurface Weight"].default_value = sss
        b.inputs["Subsurface Radius"].default_value = (1.0, 0.4, 0.25)
        b.inputs["Subsurface Scale"].default_value = 0.04
    if coat:
        b.inputs["Coat Weight"].default_value = coat
    return m


def sphere(loc, r, m, scale=(1, 1, 1), seg=48, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=seg, ring_count=seg // 2)
    o = bpy.context.object
    o.scale = scale
    o.rotation_euler = rot
    bpy.ops.object.shade_smooth()
    o.data.materials.append(m)
    return o


def capsule(p1, p2, r, m, r2=None):
    p1, p2 = Vector(p1), Vector(p2)
    d = p2 - p1
    r2 = r2 or r
    bpy.ops.mesh.primitive_cone_add(radius1=r, radius2=r2, depth=d.length, location=(p1 + p2) / 2, vertices=32)
    o = bpy.context.object
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = d.to_track_quat("Z", "Y")
    bpy.ops.object.shade_smooth()
    o.data.materials.append(m)
    sphere(p1, r, m, seg=24)
    sphere(p2, r2, m, seg=24)
    return o


def cone(loc, r1, r2, depth, m):
    bpy.ops.mesh.primitive_cone_add(radius1=r1, radius2=r2, depth=depth, location=loc, vertices=64)
    o = bpy.context.object
    bpy.ops.object.shade_smooth()
    o.data.materials.append(m)
    mod = o.modifiers.new("b", "BEVEL")
    mod.width = 0.05
    mod.segments = 5
    mod = o.modifiers.new("s", "SUBSURF")
    mod.levels = 1
    mod.render_levels = 2
    return o


def lina():
    skin = mat("skin", "#C98E63", 0.42, sss=0.3)
    hair = mat("hair", "#3A2415", 0.5, coat=0.3)
    dress = mat("dress", "#9B6BD3", 0.6)
    white = mat("white", "#F4F4F4", 0.12)
    iris = mat("iris", "#5A3418", 0.08)
    black = mat("black", "#050505", 0.08)
    pink = mat("pink", "#FF6FA3", 0.35)
    cheek = mat("cheek", "#F08A9A", 0.7)
    mouth_m = mat("mouth", "#7A2232", 0.4)
    tongue = mat("tongue", "#E86A7A", 0.4)
    shoe = mat("shoe", "#E85D8A", 0.3, coat=0.5)
    H0 = 1.22
    sphere((0, 0, H0), 0.55, skin, scale=(1, 0.92, 0.95))
    for s in (-1, 1):
        sphere((s * 0.54, 0.02, H0 - 0.03), 0.1, skin, scale=(0.55, 1, 1))
        e = Vector((s * 0.2, -0.44, H0 + 0.0))
        if pose == "blink":
            sphere(e + Vector((0, -0.02, -0.01)), 0.12, skin, scale=(1, 0.45, 0.25))
            capsule(e + Vector((-0.09, -0.07, 0)), e + Vector((0.09, -0.07, 0)), 0.012, black)
        else:
            sphere(e, 0.125, white, scale=(1, 0.45, 1.18))
            sphere(e + Vector((0, -0.04, -0.012)), 0.095, iris, scale=(1, 0.38, 1.12))
            sphere(e + Vector((0, -0.062, -0.012)), 0.052, black, scale=(1, 0.35, 1.05))
            sphere(e + Vector((-0.032, -0.08, 0.045)), 0.026, white, scale=(1, 0.5, 1))
            sphere(e + Vector((0.035, -0.078, -0.045)), 0.013, white, scale=(1, 0.5, 1))
            # eyelashes
            capsule(e + Vector((s * 0.1, -0.03, 0.1)), e + Vector((s * 0.16, -0.03, 0.15)), 0.012, black)
        sphere((s * 0.33, -0.43, H0 - 0.15), 0.075, cheek, scale=(1, 0.35, 0.65))
        sphere((s * 0.5, 0.08, H0 + 0.34), 0.25, hair)
        sphere((s * 0.33, -0.02, H0 + 0.27), 0.065, pink, scale=(1, 1, 0.8))
        # legs + shoes
        capsule((s * 0.12, 0, 0.2), (s * 0.12, 0, 0.02), 0.075, skin)
        sphere((s * 0.12, -0.05, 0.0), 0.1, shoe, scale=(0.95, 1.35, 0.6))
    # arms
    capsule((-0.26, 0, 0.6), (-0.36, -0.02, 0.3), 0.07, skin, 0.065)
    sphere((-0.37, -0.03, 0.25), 0.085, skin)
    if pose == "wave":
        capsule((0.26, 0, 0.62), (0.62, -0.12, 0.95), 0.07, skin, 0.065)
        sphere((0.66, -0.14, 1.02), 0.095, skin, scale=(0.85, 0.6, 1.15))
    else:
        capsule((0.26, 0, 0.6), (0.36, -0.02, 0.3), 0.07, skin, 0.065)
        sphere((0.37, -0.03, 0.25), 0.085, skin)
    # hair: back cap, fringe locks
    sphere((0, 0.06, H0 + 0.1), 0.565, hair, scale=(1.02, 0.97, 0.92))
    sphere((0, -0.3, H0 + 0.33), 0.4, hair, scale=(1.12, 0.6, 0.42))
    sphere((-0.2, -0.38, H0 + 0.26), 0.16, hair, scale=(1.2, 0.6, 0.6))
    sphere((0, -0.505, H0 - 0.08), 0.032, skin)
    if pose == "talk":
        sphere((0, -0.49, H0 - 0.22), 0.075, mouth_m, scale=(1, 0.4, 0.85))
        sphere((0, -0.51, H0 - 0.26), 0.045, tongue, scale=(1, 0.4, 0.5))
    else:
        bpy.ops.mesh.primitive_torus_add(location=(0, -0.475, H0 - 0.18), major_radius=0.075,
                                         minor_radius=0.018, rotation=(math.radians(90), 0, 0))
        mo = bpy.context.object
        bpy.ops.object.shade_smooth()
        mo.data.materials.append(mouth_m)
        # keep only the lower half of the ring: a smile
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="DESELECT")
        bpy.ops.object.mode_set(mode="OBJECT")
        for v in mo.data.vertices:
            v.select = v.co.y > 0.005
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.delete(type="VERT")
        bpy.ops.object.mode_set(mode="OBJECT")
    cone((0, 0, 0.44), 0.36, 0.19, 0.56, dress)
    sphere((0, -0.05, 0.69), 0.18, white, scale=(1.15, 0.8, 0.3))
    for z in (0.32, 0.45):
        sphere((0, -0.26 - (0.45 - z) * 0.25, z), 0.03, white, scale=(1, 0.5, 1))
    sphere((0, 0, 0.74), 0.12, skin)


def park():
    grass = mat("grass", "#6CC04A", 0.85)
    trunk = mat("trunk", "#8A5A34", 0.7)
    leaf = mat("leaf", "#4FAF4A", 0.55)
    leaf2 = mat("leaf2", "#6CCB5A", 0.55)
    fence = mat("fence", "#FFFFFF", 0.4)
    fl = [mat("f%d" % i, c, 0.45) for i, c in enumerate(["#FF8FB1", "#FFFFFF", "#FFB347", "#C9A0FF"])]
    yel = mat("yel", "#FFD23F", 0.4)
    bpy.ops.mesh.primitive_plane_add(size=80, location=(0, 0, -0.08))
    bpy.context.object.data.materials.append(grass)
    for x, y, z, sx in ((-9, 18, -2.5, 9), (8, 22, -3, 11)):
        sphere((x, y, z), 5, grass, scale=(sx / 5, 1, 1))

    def tree(x, y, s):
        capsule((x, y, 0), (x, y, 1.6 * s), 0.14 * s, trunk, 0.1 * s)
        for dx, dz, r, m in ((0, 2.2, 0.95, leaf), (-0.65, 1.8, 0.7, leaf), (0.65, 1.85, 0.7, leaf2),
                             (0, 2.9, 0.62, leaf2)):
            sphere((x + dx * s, y, dz * s), r * s, m)
    tree(-3.2, 3.5, 1.2)
    tree(3.4, 4.5, 1.4)
    tree(-6, 8, 1.6)
    for k in range(22):
        x = -6 + k * 0.55
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, 6, 0.45))
        o = bpy.context.object
        o.scale = (0.18, 0.05, 0.9)
        o.data.materials.append(fence)
        mod = o.modifiers.new("b", "BEVEL")
        mod.width = 0.03
        mod.segments = 3
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 6.03, 0.55))
    o = bpy.context.object
    o.scale = (12.5, 0.04, 0.1)
    o.data.materials.append(fence)
    r = random.Random(3)
    for i in range(70):
        x, y = r.uniform(-5, 5), r.uniform(-1.6, 5)
        if abs(x) < 0.9 and y < 0.8:
            continue
        c = (x, y, 0.06)
        for k in range(5):
            a = k * 2 * math.pi / 5
            sphere((x + math.cos(a) * 0.06, y + math.sin(a) * 0.06, 0.06), 0.045, fl[i % 4],
                   scale=(1, 1, 0.4), seg=12)
        sphere(c, 0.035, yel, scale=(1, 1, 0.6), seg=12)


if layer in ("bg", "all"):
    park()
if layer in ("char", "all"):
    lina()
if layer == "char":
    # shadow catcher ground so she still casts a soft shadow when composited
    bpy.ops.mesh.primitive_plane_add(size=6, location=(0, 0, -0.08))
    bpy.context.object.is_shadow_catcher = True

w = bpy.data.worlds.new("w")
S.world = w
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (*srgb("#9FD6FF"), 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 1.3
bpy.ops.object.light_add(type="SUN", location=(4, -4, 8))
L = bpy.context.object
L.data.energy = 3.2
L.data.angle = math.radians(12)
L.rotation_euler = (math.radians(48), 0, math.radians(30))
bpy.ops.object.light_add(type="AREA", location=(-2.2, -3.5, 2.6))
F = bpy.context.object
F.data.energy = 150
F.data.size = 3
F.rotation_euler = (math.radians(62), 0, math.radians(-32))
bpy.ops.object.light_add(type="AREA", location=(0, 2.5, 2.8))
R = bpy.context.object
R.data.energy = 80
R.data.size = 2
R.rotation_euler = (math.radians(-60), 0, 0)
bpy.ops.object.camera_add(location=(0, -4.6, 1.0))
C = bpy.context.object
S.camera = C
C.rotation_euler = (math.radians(86), 0, 0)
C.data.lens = 40
S.render.engine = "CYCLES"
S.cycles.device = "CPU"
S.cycles.samples = 40
S.cycles.use_denoising = True
S.render.resolution_x, S.render.resolution_y = 1920, 1080
S.render.resolution_percentage = 67
S.render.film_transparent = layer == "char"
S.view_settings.view_transform = "AgX"
S.view_settings.look = "AgX - Punchy"
S.render.image_settings.color_mode = "RGBA" if layer == "char" else "RGB"
S.render.filepath = out
t = time.time()
bpy.ops.render.render(write_still=True)
print("render", round(time.time() - t, 1), "s")
