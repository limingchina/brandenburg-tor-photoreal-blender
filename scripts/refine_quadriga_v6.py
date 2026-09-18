"""Geometry-only quadriga refinement guided by front/side/rear viewer screenshots.

Run with Blender 5.2 in background on the packed v5 scene.  The screenshots are
visual references only; no screenshot pixels or Meshy mesh data are used.
"""

import bpy
import math
import os
from mathutils import Vector


ROOT = r"C:\Users\china\Documents\Codex\2026-09-13\can"
OUT = os.path.join(ROOT, "outputs")
BLEND_OUT = os.path.join(OUT, "brandenburg_tor_photoreal_v6.blend")
scene = bpy.context.scene

bronze = bpy.data.materials["MAT_ATLAS_QUADRIGA_BRONZE_V3"]
bronze_dark = bpy.data.materials["MAT_ATLAS_QUADRIGA_BRONZE_DARK_V3"]

old = bpy.data.collections.get("QUADRIGA_SCULPT_V6")
if old:
    for obj in list(old.all_objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(old)
detail = bpy.data.collections.new("QUADRIGA_SCULPT_V6")
scene.collection.children.link(detail)


def link_detail(obj, material):
    for collection in list(obj.users_collection):
        collection.objects.unlink(obj)
    detail.objects.link(obj)
    if obj.type == "MESH":
        obj.data.materials.clear()
        obj.data.materials.append(material)
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
    obj["v6_reference"] = "Geometry interpreted from user-provided front, side and rear viewer screenshots"
    return obj


def mesh_object(name, vertices, faces, material, bevel=0.0):
    mesh = bpy.data.meshes.new(name + " mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    detail.objects.link(obj)
    obj.data.materials.append(material)
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    if bevel:
        modifier = obj.modifiers.new("Soft bronze edge", "BEVEL")
        modifier.width = bevel
        modifier.segments = 2
    return obj


def feather(name, root, tip, width, material, curvature=0.09):
    root = Vector(root)
    tip = Vector(tip)
    along = tip - root
    broad = Vector((-along.z, 0.0, along.x)).normalized()
    depth = Vector((0.0, 1.0, 0.0))
    verts = []
    rings = 12
    for j in range(rings + 1):
        t = j / rings
        c = root.lerp(tip, t)
        c.y += curvature * math.sin(math.pi * t)
        w = width * max(0.018, math.sin(math.pi * t) ** 0.78)
        d = width * 0.13 * max(0.08, math.sin(math.pi * t))
        verts.extend((c - broad * w, c - depth * d,
                      c + broad * w, c + depth * d))
    faces = []
    for j in range(rings):
        a, b = j * 4, (j + 1) * 4
        faces.extend(((a, a + 1, b + 1, b), (a + 1, a + 2, b + 2, b + 1),
                      (a + 2, a + 3, b + 3, b + 2), (a + 3, a, b, b + 3)))
    faces.extend(((0, 3, 2, 1), (rings * 4, rings * 4 + 1, rings * 4 + 2, rings * 4 + 3)))
    return mesh_object(name, verts, faces, material, 0.005)


# The v5 wings were splayed like an emblem.  The real wings flank Victoria's
# back, rising slightly at the shoulders and falling toward the chariot rim.
removed_wings = []
for obj in list(bpy.data.objects):
    if obj.name.startswith(("Victoria wing shoulder", "Victoria wing spar", "Victoria primary feather",
                            "Victoria secondary feather", "Victoria covert feather")):
        removed_wings.append(obj.name)
        bpy.data.objects.remove(obj, do_unlink=True)

for side in (-1, 1):
    verts = []
    sections = 12
    for j in range(sections + 1):
        t = j / sections
        z = 23.45 - 1.25 * t
        x = side * (0.30 + 0.29 * math.sin(math.pi * t * 0.72))
        y = 1.86 + 0.19 * t
        half_width = (0.20 + 0.08 * math.sin(math.pi * t)) * (1 - 0.48 * t)
        half_depth = 0.07 * (1 - 0.6 * t)
        verts.extend(((x - half_width, y, z), (x, y - half_depth, z),
                      (x + half_width, y, z), (x, y + half_depth, z)))
    faces = []
    for j in range(sections):
        a, b = j * 4, (j + 1) * 4
        faces.extend(((a, a + 1, b + 1, b), (a + 1, a + 2, b + 2, b + 1),
                      (a + 2, a + 3, b + 3, b + 2), (a + 3, a, b, b + 3)))
    faces.extend(((0, 3, 2, 1), (sections * 4, sections * 4 + 1, sections * 4 + 2, sections * 4 + 3)))
    mesh_object(f"Victoria v6 folded wing core {side}", verts, faces, bronze, 0.025)

    for j in range(24):
        t = j / 23
        x = side * (0.23 + 0.39 * t)
        z = 23.33 - 0.92 * t
        root = (x, 1.87 + 0.13 * t, z)
        tip = (x + side * (0.15 - 0.045 * t), 2.06 + 0.11 * t, z - 0.28 - 0.16 * t)
        feather(f"Victoria v6 primary {side}:{j}", root, tip,
                0.058 - 0.013 * t, bronze_dark if j % 5 == 0 else bronze)
    for j in range(17):
        t = j / 16
        root = (side * (0.24 + 0.25 * t), 1.81 + 0.10 * t, 23.41 - 0.68 * t)
        tip = (side * (0.45 + 0.22 * t), 1.99 + 0.12 * t, 23.10 - 0.71 * t)
        feather(f"Victoria v6 covert {side}:{j}", root, tip, 0.061, bronze)


# Replace the fine radial-rod wheel spokes with broad eight-spoke cast wheels.
removed_spokes = []
for obj in list(bpy.data.objects):
    if obj.name.startswith("Wheel ") and " spoke " in obj.name:
        removed_spokes.append(obj.name)
        bpy.data.objects.remove(obj, do_unlink=True)

for side in (-1, 1):
    x = side * 1.14
    cy, cz = 1.74, 20.96
    for j in range(8):
        angle = 2.0 * math.pi * j / 8
        radial = Vector((math.cos(angle), math.sin(angle)))
        tangential = Vector((-math.sin(angle), math.cos(angle)))
        verts = []
        for radius, half_width in ((0.13, 0.070), (0.70, 0.115)):
            for thickness in (-0.055, 0.055):
                for across in (-half_width, half_width):
                    yz = Vector((cy, cz)) + radial * radius + tangential * across
                    verts.append((x + thickness, yz.x, yz.y))
        faces = ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1),
                 (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3))
        mesh_object(f"Chariot v6 broad wheel spoke {side}:{j}", verts, faces, bronze, 0.018)
    bpy.ops.mesh.primitive_torus_add(
        major_radius=0.77, minor_radius=0.040,
        major_segments=72, minor_segments=12,
        location=(side * 1.20, cy, cz), rotation=(0, math.pi / 2, 0),
    )
    ring = bpy.context.object
    ring.name = f"Chariot v6 wheel inner cast lip {side}"
    link_detail(ring, bronze)


# Add a shallow convex bronze front to the chariot.  The old thin rectangular
# breastwork remains behind it as structural backing.
verts = []
nx, nz = 24, 8
for iz in range(nz + 1):
    t = iz / nz
    for ix in range(nx + 1):
        u = -1.0 + 2.0 * ix / nx
        x = u * (0.95 - 0.08 * t)
        y = 0.80 - 0.17 * (1.0 - u * u) + 0.06 * math.sin(math.pi * t)
        z = 21.30 + t * (0.94 - 0.12 * u * u)
        verts.append((x, y, z))
faces = []
for iz in range(nz):
    for ix in range(nx):
        a = iz * (nx + 1) + ix
        faces.append((a, a + 1, a + nx + 2, a + nx + 1))
breastwork = mesh_object("Chariot v6 bowed bronze front", verts, faces, bronze, 0.022)
solidify = breastwork.modifiers.new("Cast panel thickness", "SOLIDIFY")
solidify.thickness = 0.075


# The horse source already has an alternating trot.  Sculpt the planted foreleg
# on the outer pair into a more conspicuous lifted gesture; retain the original
# high-detail vertex topology and avoid touching head/torso geometry.
posed_vertices = {}
for index in (1, 4):
    changed = 0
    for suffix in ("anatomical body", "mane, tail and hooves"):
        obj = bpy.data.objects[f"Horse {index} {suffix}"]
        obj.data = obj.data.copy()
        obj.data.name = f"Horse {index} v6 individually posed {suffix}"
        for vertex in obj.data.vertices:
            x, y, z = vertex.co
            x_weight = math.exp(-((x - 0.112) / 0.072) ** 2)
            y_weight = math.exp(-((y + 0.11) / 0.25) ** 2)
            z_weight = max(0.0, min(1.0, (-z - 0.14) / 0.40))
            weight = x_weight * y_weight * z_weight
            if weight < 0.001:
                continue
            vertex.co.y -= 0.12 * weight
            vertex.co.z += 0.15 * weight
            changed += 1
        obj.data.update()
    posed_vertices[index] = changed

# The v5 add-on ears read as tall spikes at this scale.  Reduce just their
# vertical reach; keep the underlying imported ears and inset detail intact.
for obj in bpy.data.objects:
    if obj.name.startswith("Horse ") and ("outer ear" in obj.name or "inner ear" in obj.name):
        obj.scale.z *= 0.66

# A broad frontal bounce reveals the existing patina/normal relief without
# replacing the atlas or washing out the bronze's darker recesses.
bpy.ops.object.light_add(type="AREA", location=(0.0, -10.0, 27.5))
front_fill = bpy.context.object
front_fill.name = "Quadriga frontal museum bounce V6"
front_fill.data.energy = 3500.0
front_fill.data.shape = "DISK"
front_fill.data.size = 8.0
front_fill.rotation_euler = (Vector((0.0, 0.5, 22.7)) - front_fill.location).to_track_quat("-Z", "Y").to_euler()


scene["version"] = "6.0 screenshot-guided quadriga geometry refinement"
scene["v6_shape_changes"] = (
    "Folded feathered Victoria wings, eight broad spokes per wheel, bowed chariot panel, "
    "individually lifted outer forelegs; no Meshy mesh extraction"
)
scene["v6_reference_policy"] = "User-supplied screenshots used as visual geometry reference only; pixels not embedded"

main_cam = bpy.data.objects.get("CAM_Main_Photoreal")
front_cam = bpy.data.objects.get("CAM_Quadriga_Closeup")
profile_cam = bpy.data.objects.get("CAM_Quadriga_Profile")
rear_cam = bpy.data.objects.get("CAM_Quadriga_Rear_V6")
if rear_cam is None:
    data = bpy.data.cameras.new("CAM_Quadriga_Rear_V6")
    rear_cam = bpy.data.objects.new("CAM_Quadriga_Rear_V6", data)
    scene.collection.objects.link(rear_cam)
rear_cam.location = (0.0, 32.0, 25.0)
rear_cam.data.lens = 82
rear_cam.data.dof.use_dof = False
rear_cam.rotation_euler = (Vector((0.0, 0.0, 23.0)) - rear_cam.location).to_track_quat("-Z", "Y").to_euler()

scene.render.engine = "BLENDER_EEVEE"
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.resolution_percentage = 100
scene.render.image_settings.compression = 24

bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT)

for camera, width, height, filename in (
    (front_cam, 1200, 900, "brandenburg_tor_photoreal_v6_quadriga_front.png"),
    (profile_cam, 1200, 900, "brandenburg_tor_photoreal_v6_quadriga_profile.png"),
    (rear_cam, 1200, 900, "brandenburg_tor_photoreal_v6_quadriga_rear.png"),
    (main_cam, 1280, 720, "brandenburg_tor_photoreal_v6_preview.png"),
):
    if camera is None:
        continue
    scene.camera = camera
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.filepath = os.path.join(OUT, filename)
    bpy.ops.render.render(write_still=True)

if main_cam:
    scene.camera = main_cam
bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT)
print("V6_SHAPE", "removed_wings", len(removed_wings), "removed_spokes", len(removed_spokes))
print("V6_FORELEG_VERTICES", posed_vertices)
print("V6_SAVED", BLEND_OUT)
