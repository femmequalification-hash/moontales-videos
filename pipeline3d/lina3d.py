"""Prototype: a cute 3D Lina in a park, rendered with Blender Cycles (free)."""
import bpy, math, sys, time
from mathutils import Vector

out = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "/tmp/lina3d.png"
bpy.ops.wm.read_factory_settings(use_empty=True)
S = bpy.context.scene

def mat(name, rgb, rough=0.5, sss=0.0, spec=0.5, emit=None):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    if sss:
        b.inputs["Subsurface Weight"].default_value = sss
        b.inputs["Subsurface Radius"].default_value = (1.0, 0.35, 0.2)
        b.inputs["Subsurface Scale"].default_value = 0.05
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = 1.0
    return m

def srgb(h):
    h = h.lstrip("#"); c = [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)

def sphere(loc, r, m, scale=(1, 1, 1), seg=48):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=seg, ring_count=seg // 2)
    o = bpy.context.object; o.scale = scale; bpy.ops.object.shade_smooth(); o.data.materials.append(m); return o

def capsule(p1, p2, r, m):
    p1, p2 = Vector(p1), Vector(p2); d = p2 - p1
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=d.length, location=(p1 + p2) / 2, vertices=32)
    o = bpy.context.object; o.rotation_mode = "QUATERNION"; o.rotation_quaternion = d.to_track_quat("Z", "Y")
    bpy.ops.object.shade_smooth(); o.data.materials.append(m)
    sphere(p1, r, m, seg=24); sphere(p2, r, m, seg=24); return o

def cone(loc, r1, r2, depth, m):
    bpy.ops.mesh.primitive_cone_add(radius1=r1, radius2=r2, depth=depth, location=loc, vertices=48)
    o = bpy.context.object; bpy.ops.object.shade_smooth(); o.data.materials.append(m)
    mod = o.modifiers.new("b", "BEVEL"); mod.width = 0.04; mod.segments = 4; return o

skin = mat("skin", srgb("#C98E63"), 0.45, sss=0.25)
hair = mat("hair", srgb("#3A2415"), 0.55)
dress = mat("dress", srgb("#9B6BD3"), 0.6)
white = mat("white", (0.95, 0.95, 0.95), 0.15)
iris = mat("iris", srgb("#4A2B18"), 0.1)
black = mat("black", (0.01, 0.01, 0.01), 0.1)
pink = mat("pink", srgb("#FF6FA3"), 0.4)
cheek = mat("cheek", srgb("#F08A9A"), 0.6)
mouth = mat("mouth", srgb("#8C2F3A"), 0.4)
shoe = mat("shoe", srgb("#E85D8A"), 0.35)
grass = mat("grass", srgb("#6CC04A"), 0.8)
trunk = mat("trunk", srgb("#8A5A34"), 0.7)
leaf = mat("leaf", srgb("#4FAF4A"), 0.6)
flower_m = [mat("f%d" % i, srgb(c), 0.5) for i, c in enumerate(["#FF8FB1", "#FFFFFF", "#FFB347"])]

# ---- Lina (toddler proportions: big head)
H0 = 1.25  # head centre height
sphere((0, 0, H0), 0.55, skin, scale=(1, 0.95, 0.97))
for s in (-1, 1):  # ears
    sphere((s * 0.53, 0, H0 - 0.02), 0.1, skin, scale=(0.6, 1, 1))
    # eyes
    e = Vector((s * 0.2, -0.47, H0 + 0.02))
    sphere(e, 0.13, white, scale=(1, 0.6, 1.15))
    sphere(e + Vector((0, -0.055, -0.01)), 0.095, iris, scale=(1, 0.5, 1.1))
    sphere(e + Vector((0, -0.085, -0.01)), 0.05, black, scale=(1, 0.5, 1))
    sphere(e + Vector((-0.03, -0.11, 0.045)), 0.025, white)
    sphere(e + Vector((0.035, -0.105, -0.045)), 0.012, white)
    sphere((s * 0.34, -0.43, H0 - 0.17), 0.08, cheek, scale=(1, 0.4, 0.7))
    # hair puffs + ties
    sphere((s * 0.52, 0.05, H0 + 0.33), 0.26, hair)
    sphere((s * 0.36, -0.02, H0 + 0.25), 0.07, pink, scale=(1, 1, 0.8))
    # arms, hands
    capsule((s * 0.26, 0, 0.55), (s * 0.42, -0.05, 0.25), 0.07, skin)
    sphere((s * 0.43, -0.07, 0.2), 0.085, skin)
    # legs, shoes
    capsule((s * 0.12, 0, 0.18), (s * 0.12, 0, 0.0), 0.07, skin)
    sphere((s * 0.12, -0.06, -0.02), 0.1, shoe, scale=(0.9, 1.4, 0.6))
sphere((0, 0.04, H0 + 0.12), 0.565, hair, scale=(1.02, 0.98, 0.9))  # hair cap (behind face)
sphere((0, -0.40, H0 + 0.33), 0.32, hair, scale=(1.3, 0.55, 0.42))  # fringe
sphere((0, -0.53, H0 - 0.08), 0.035, skin)  # nose
bpy.ops.mesh.primitive_torus_add(location=(0, -0.48, H0 - 0.21), major_radius=0.08, minor_radius=0.022,
                                 rotation=(math.radians(80), 0, 0))
m_o = bpy.context.object; bpy.ops.object.shade_smooth(); m_o.data.materials.append(mouth)
m_o.scale = (1, 1, 0.5)
cone((0, 0, 0.42), 0.36, 0.2, 0.55, dress)            # dress
sphere((0, -0.06, 0.66), 0.17, white, scale=(1.2, 0.8, 0.35))  # collar
sphere((0, 0, 0.72), 0.12, skin)                         # neck

# ---- scene
bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, -0.08)); bpy.context.object.data.materials.append(grass)
def tree(x, y, s):
    capsule((x, y, 0), (x, y, 1.6 * s), 0.12 * s, trunk)
    for dx, dz, r in ((0, 2.2, 0.9), (-0.6, 1.8, 0.65), (0.6, 1.8, 0.65), (0, 2.8, 0.6)):
        sphere((x + dx * s, y, dz * s), r * s, leaf)
tree(-2.6, 3, 1.1); tree(2.9, 4, 1.3)
import random; r = random.Random(3)
for i in range(30):
    x, y = r.uniform(-4, 4), r.uniform(-1.5, 3)
    if abs(x) < 0.8 and y < 0.6: continue
    sphere((x, y, 0.02), 0.07, flower_m[i % 3], scale=(1, 1, 0.5), seg=16)

w = bpy.data.worlds.new("w"); S.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (*srgb("#9FD6FF"), 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 1.2
bpy.ops.object.light_add(type="SUN", location=(4, -4, 8)); L = bpy.context.object
L.data.energy = 3.5; L.data.angle = math.radians(10); L.rotation_euler = (math.radians(45), 0, math.radians(35))
bpy.ops.object.light_add(type="AREA", location=(-2, -3, 2.5)); F = bpy.context.object
F.data.energy = 120; F.data.size = 3; F.rotation_euler = (math.radians(60), 0, math.radians(-35))
bpy.ops.object.camera_add(location=(0, -4.2, 1.15)); C = bpy.context.object; S.camera = C
C.rotation_euler = (math.radians(86), 0, 0); C.data.lens = 50
C.data.dof.use_dof = True; C.data.dof.focus_distance = 3.7; C.data.dof.aperture_fstop = 4

S.render.engine = "CYCLES"; S.cycles.device = "CPU"; S.cycles.samples = 48; S.cycles.use_denoising = True
S.render.resolution_x, S.render.resolution_y = 1280, 720
S.view_settings.view_transform = "AgX"; S.view_settings.look = "AgX - Punchy"
S.render.filepath = out
t = time.time(); bpy.ops.render.render(write_still=True); print("render", round(time.time() - t, 1), "s")
