import bpy
import math


scene = bpy.context.scene
assert scene.get("version") == "5.0 reference-matched outer horse formation"

expected = {
    "Horse 1 high fidelity": (-2.02, math.radians(-15.5)),
    "Horse 2 high fidelity": (-0.69, math.radians(-2.0)),
    "Horse 3 high fidelity": (0.69, math.radians(2.0)),
    "Horse 4 high fidelity": (2.02, math.radians(15.5)),
}
for name, (x, yaw) in expected.items():
    horse = bpy.data.objects.get(name)
    assert horse is not None, name
    assert math.isclose(horse.location.x, x, abs_tol=1e-4), (name, horse.location.x)
    assert math.isclose(horse.rotation_euler.z, yaw, abs_tol=1e-4), (name, horse.rotation_euler.z)
    assert horse.rotation_mode == "XYZ", (name, horse.rotation_mode)

for index in (1, 4):
    harness = [obj for obj in bpy.data.objects if obj.type == "CURVE" and obj.name.startswith(f"Horse {index} ")]
    assert len(harness) == 7, (index, [obj.name for obj in harness])

maps = [image for image in bpy.data.images if image.name.startswith("brandenburg_v4_atlas_")]
assert len(maps) == 4
assert all(image.packed_file is not None for image in maps)

facial = bpy.data.collections.get("HORSE_FACIAL_DETAIL_V5")
assert facial is not None
assert len(facial.all_objects) == 32, len(facial.all_objects)
assert sum(1 for obj in facial.all_objects if " eye " in obj.name) == 8
assert sum(1 for obj in facial.all_objects if "outer ear" in obj.name) == 8

print("VERIFY_V5_OK")
print("VERSION", scene.get("version"))
print("FORMATION", scene.get("quadriga_formation"))
print("PACKED_MAPS", sorted(image.name for image in maps))
print("FACIAL_DETAIL_OBJECTS", len(facial.all_objects))
