import bpy
import math
import os
from mathutils import Matrix, Vector


ROOT = r"C:\Users\china\Documents\Codex\2026-09-13\can"
OUT = os.path.join(ROOT, "outputs")
BLEND_OUT = os.path.join(OUT, "brandenburg_tor_photoreal_v5.blend")


def look_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def transform_outer_harness(horse_index, old_pivot, new_pivot, delta_yaw):
    """Move horse-end harness points while retaining chariot/Victoria anchors."""
    rotation = Matrix.Rotation(delta_yaw, 4, "Z")
    old_pivot = Vector(old_pivot)
    new_pivot = Vector(new_pivot)
    changed = []
    prefix = f"Horse {horse_index} "
    for obj in bpy.data.objects:
        if obj.type != "CURVE" or not obj.name.startswith(prefix):
            continue
        for spline in obj.data.splines:
            points = spline.bezier_points if spline.type == "BEZIER" else spline.points
            for point in points:
                co = Vector(point.co[:3])
                transformed = rotation @ (co - old_pivot) + new_pivot
                # Points at the bridle/collar move fully. Reins and traces blend
                # back to their fixed chariot/Victoria attachment points.
                weight = max(0.0, min(1.0, (0.95 - co.y) / 1.70))
                result = co.lerp(transformed, weight)
                if spline.type == "BEZIER":
                    point.co = result
                else:
                    point.co = (*result, point.co.w)
        changed.append(obj.name)
    return changed


layout = {
    1: {"name": "Horse 1 high fidelity", "x": -2.02, "y": 0.02, "z": 20.31, "yaw": math.radians(-15.5)},
    2: {"name": "Horse 2 high fidelity", "x": -0.69, "y": -0.19, "z": 20.28, "yaw": math.radians(-2.0)},
    3: {"name": "Horse 3 high fidelity", "x": 0.69, "y": -0.19, "z": 20.28, "yaw": math.radians(2.0)},
    4: {"name": "Horse 4 high fidelity", "x": 2.02, "y": 0.02, "z": 20.31, "yaw": math.radians(15.5)},
}

changed_harness = []
for index, pose in layout.items():
    horse = bpy.data.objects.get(pose["name"])
    if horse is None:
        raise RuntimeError(f"Missing {pose['name']}")
    old_pivot = Vector((horse.location.x, horse.location.y, horse.location.z))
    new_pivot = Vector((pose["x"], pose["y"], pose["z"]))
    if index in {1, 4}:
        # The source root is quaternion-driven; earlier Euler writes did not
        # affect its evaluated matrix. Harness therefore starts at zero yaw.
        changed_harness.extend(transform_outer_harness(index, old_pivot, new_pivot, pose["yaw"]))
    horse.location = new_pivot
    horse.rotation_mode = "XYZ"
    horse.rotation_euler = (0.0, 0.0, pose["yaw"])
    horse.rotation_euler.z = pose["yaw"]
    horse["v5_formation"] = "Reference-matched fanned quadriga formation"

# -----------------------------------------------------------------------------
# Horse facial detail: recessed oxidized eyes, eyelid rims, and leaf-shaped ears.
# Geometry is parented in horse-root local space, so it follows every pose.
# -----------------------------------------------------------------------------
old_detail = bpy.data.collections.get("HORSE_FACIAL_DETAIL_V5")
if old_detail:
    for obj in list(old_detail.all_objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(old_detail)

detail_collection = bpy.data.collections.new("HORSE_FACIAL_DETAIL_V5")
scene_root = bpy.context.scene.collection
scene_root.children.link(detail_collection)

bronze = bpy.data.materials.get("MAT_ATLAS_QUADRIGA_BRONZE_V3")
bronze_dark = bpy.data.materials.get("MAT_ATLAS_QUADRIGA_BRONZE_DARK_V3")
if not bronze or not bronze_dark:
    raise RuntimeError("Missing v4 bronze atlas materials")

eye_material = bpy.data.materials.get("MAT_HORSE_EYE_OXIDIZED_V5") or bpy.data.materials.new("MAT_HORSE_EYE_OXIDIZED_V5")
eye_material.use_nodes = True
eye_bsdf = eye_material.node_tree.nodes.get("Principled BSDF")
eye_bsdf.inputs["Base Color"].default_value = (0.008, 0.016, 0.012, 1.0)
eye_bsdf.inputs["Metallic"].default_value = 0.72
eye_bsdf.inputs["Roughness"].default_value = 0.20
if "Coat Weight" in eye_bsdf.inputs:
    eye_bsdf.inputs["Coat Weight"].default_value = 0.28


def put_detail(obj, horse, material):
    for collection in list(obj.users_collection):
        collection.objects.unlink(obj)
    detail_collection.objects.link(obj)
    obj.parent = horse
    if obj.type == "MESH":
        obj.data.materials.append(material)
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
    obj["v5_detail"] = "Reference-guided horse eyes and ears"
    return obj


def make_ear(name, horse, side, material, inner=False):
    root_scale = abs(horse.scale.y)
    depth_shift = -0.010 if inner else 0.0
    width_factor = 0.44 if inner else 1.0
    centers = [
        Vector((side * 0.125, -1.20 + depth_shift, 3.08)),
        Vector((side * 0.178, -1.16 + depth_shift, 3.24)),
        Vector((side * 0.225, -1.13 + depth_shift, 3.40)),
    ]
    widths = [0.046, 0.072, 0.008]
    thickness = 0.014 if inner else 0.028
    verts = []
    for center, width in zip(centers, widths):
        width *= width_factor
        for yoff in (-thickness, thickness):
            verts.append(tuple((center + Vector((-width, yoff, 0.0))) / root_scale))
            verts.append(tuple((center + Vector((width, yoff, 0.0))) / root_scale))
    faces = []
    for station in range(2):
        a = station * 4
        b = (station + 1) * 4
        faces.extend(((a, a + 1, b + 1, b), (a + 2, b + 2, b + 3, a + 3),
                      (a, b, b + 2, a + 2), (a + 1, a + 3, b + 3, b + 1)))
    faces.extend(((0, 2, 3, 1), (8, 9, 11, 10)))
    mesh = bpy.data.meshes.new(name + " Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    ear = bpy.data.objects.new(name, mesh)
    detail_collection.objects.link(ear)
    ear.parent = horse
    ear.data.materials.append(material)
    bevel = ear.modifiers.new("Sculpted ear edge", "BEVEL")
    bevel.width = 0.008 / root_scale
    bevel.segments = 3
    return ear


for index in range(1, 5):
    horse = bpy.data.objects.get(f"Horse {index} high fidelity")
    root_scale = abs(horse.scale.y)
    for side in (-1, 1):
        # Dark, slightly protruding eyeball seated inside a patinated bronze rim.
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=20, radius=1.0)
        eye = bpy.context.object
        eye.name = f"Horse {index} eye {'L' if side < 0 else 'R'}"
        eye.location = (side * 0.150 / root_scale, -1.58 / root_scale, 3.00 / root_scale)
        eye.scale = (0.038 / root_scale, 0.026 / root_scale, 0.032 / root_scale)
        put_detail(eye, horse, eye_material)

        bpy.ops.mesh.primitive_torus_add(
            major_radius=0.043 / root_scale,
            minor_radius=0.006 / root_scale,
            major_segments=40,
            minor_segments=10,
        )
        lid = bpy.context.object
        lid.name = f"Horse {index} sculpted eyelid {'L' if side < 0 else 'R'}"
        lid.location = (side * 0.150 / root_scale, -1.605 / root_scale, 3.00 / root_scale)
        lid.rotation_euler = (math.pi / 2, 0.0, 0.0)
        lid.scale.y = 0.72
        put_detail(lid, horse, bronze)

        make_ear(f"Horse {index} outer ear {'L' if side < 0 else 'R'}", horse, side, bronze, False)
        make_ear(f"Horse {index} inner ear {'L' if side < 0 else 'R'}", horse, side, bronze_dark, True)

scene = bpy.context.scene
scene["version"] = "5.0 reference-matched outer horse formation"
scene["quadriga_formation"] = "Outer horses evaluated at 15.5 degrees outward and positioned at +/-2.02 m; harness horse-ends follow the pose."

main_cam = bpy.data.objects.get("CAM_Main_Photoreal")
quad_cam = bpy.data.objects.get("CAM_Quadriga_Closeup")
profile_cam = bpy.data.objects.get("CAM_Quadriga_Profile")
if quad_cam:
    quad_cam.location = (0.0, -32.5, 25.1)
    quad_cam.data.lens = 82
    quad_cam.data.dof.aperture_fstop = 11
    look_at(quad_cam, (0.0, -0.15, 23.12))
if profile_cam:
    profile_cam.location = (-18.5, -20.5, 25.5)
    profile_cam.data.lens = 72
    look_at(profile_cam, (0.0, 0.15, 23.05))

scene.render.engine = "BLENDER_EEVEE"
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.image_settings.color_depth = "8"
scene.render.resolution_percentage = 100
scene.view_settings.look = "AgX - Medium High Contrast"

bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT)

if main_cam:
    scene.camera = main_cam
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.filepath = os.path.join(OUT, "brandenburg_tor_photoreal_v5_preview.png")
    bpy.ops.render.render(write_still=True)

if quad_cam:
    scene.camera = quad_cam
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 900
    scene.render.filepath = os.path.join(OUT, "brandenburg_tor_photoreal_v5_quadriga_closeup.png")
    bpy.ops.render.render(write_still=True)

if profile_cam:
    scene.camera = profile_cam
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 900
    scene.render.filepath = os.path.join(OUT, "brandenburg_tor_photoreal_v5_quadriga_profile.png")
    bpy.ops.render.render(write_still=True)

if main_cam:
    scene.camera = main_cam
bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT)

print("V5_LAYOUT", {index: (pose["x"], pose["y"], math.degrees(pose["yaw"])) for index, pose in layout.items()})
print("ADJUSTED_HARNESS", sorted(changed_harness))
print("SAVED", BLEND_OUT)
