import bpy
import math


scene = bpy.context.scene
assert scene.get("version") == "6.0 screenshot-guided quadriga geometry refinement"

atlas = [image for image in bpy.data.images if image.name.startswith("brandenburg_v4_atlas_")]
assert len(atlas) == 4
assert all(image.packed_file is not None for image in atlas)

for index, x, yaw in ((1, -2.02, -15.5), (2, -0.69, -2.0),
                      (3, 0.69, 2.0), (4, 2.02, 15.5)):
    horse = bpy.data.objects[f"Horse {index} high fidelity"]
    assert math.isclose(horse.location.x, x, abs_tol=1e-4)
    assert math.isclose(horse.rotation_euler.z, math.radians(yaw), abs_tol=1e-4)
    assert bpy.data.objects.get(f"Horse {index} eye L") is not None
    assert bpy.data.objects.get(f"Horse {index} eye R") is not None

assert bpy.data.objects["Horse 1 anatomical body"].data is not bpy.data.objects["Horse 2 anatomical body"].data
assert bpy.data.objects["Horse 4 anatomical body"].data is not bpy.data.objects["Horse 3 anatomical body"].data

sculpt = bpy.data.collections.get("QUADRIGA_SCULPT_V6")
assert sculpt is not None
assert sum("v6 folded wing core" in obj.name for obj in sculpt.all_objects) == 2
assert sum("Victoria v6 primary" in obj.name for obj in sculpt.all_objects) == 48
assert sum("Victoria v6 covert" in obj.name for obj in sculpt.all_objects) == 34
assert sum("broad wheel spoke" in obj.name for obj in sculpt.all_objects) == 16
assert bpy.data.objects.get("Chariot v6 bowed bronze front") is not None
assert bpy.data.objects.get("CAM_Quadriga_Rear_V6") is not None
assert bpy.data.objects.get("Quadriga frontal museum bounce V6") is not None
assert not any(obj.name.startswith("Victoria primary feather") for obj in bpy.data.objects)

print("VERIFY_V6_OK")
print("PACKED_ATLAS_MAPS", sorted(image.name for image in atlas))
print("SCULPT_OBJECTS", len(sculpt.all_objects))
