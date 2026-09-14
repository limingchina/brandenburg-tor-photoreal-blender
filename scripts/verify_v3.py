import bpy
import os

coll = bpy.data.collections.get("QUADRIGA_REFERENCE_MATCHED")
if coll is None:
    raise RuntimeError("Quadriga collection missing")

meshes = [o for o in coll.all_objects if o.type == "MESH"]
tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in meshes)
horse_meshes = [o for o in meshes if o.name.startswith("Horse ")]
horse_tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in horse_meshes)
materials = sorted({m.name for o in coll.all_objects if hasattr(o.data, "materials") for m in o.data.materials if m})
missing = []
for image in bpy.data.images:
    if image.source == "FILE" and image.filepath:
        path = bpy.path.abspath(image.filepath)
        if not os.path.exists(path):
            missing.append(path)

assert len([o for o in coll.objects if o.name.startswith("Horse ") and o.type == "EMPTY"]) == 4
assert horse_tris >= 80000
assert any("QUADRIGA_BRONZE_V3" in name for name in materials)
assert not missing, missing

print("VERIFY_OK")
print("quadriga_objects", len(coll.all_objects))
print("quadriga_meshes", len(meshes))
print("quadriga_triangles", tris)
print("horse_meshes", len(horse_meshes))
print("horse_triangles", horse_tris)
print("materials", materials)
