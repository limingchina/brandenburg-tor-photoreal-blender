import bpy
import math


scene = bpy.context.scene
expected_maps = {
    "brandenburg_v4_atlas_albedo_2k.png",
    "brandenburg_v4_atlas_roughness_2k.png",
    "brandenburg_v4_atlas_normal_2k.png",
    "brandenburg_v4_atlas_metallic_2k.png",
}

found_maps = {image.name for image in bpy.data.images if image.name in expected_maps}
assert found_maps == expected_maps, (found_maps, expected_maps)
for image in bpy.data.images:
    if image.name in expected_maps:
        assert image.packed_file is not None, f"Not packed: {image.name}"

bronze_materials = [
    material for material in bpy.data.materials
    if material.get("atlas_region") in {"bronze", "bronze_dark"}
]
assert bronze_materials
for material in bronze_materials:
    names = {node.name for node in material.node_tree.nodes}
    assert "V4 bronze micro-pitting" in names, material.name
    assert "V4 cast bronze micro-bump" in names, material.name

expected_yaw = {
    "Horse 1 high fidelity": -0.205,
    "Horse 2 high fidelity": -0.040,
    "Horse 3 high fidelity": 0.040,
    "Horse 4 high fidelity": 0.205,
}
for name, yaw in expected_yaw.items():
    horse = bpy.data.objects.get(name)
    assert horse is not None, name
    assert math.isclose(horse.rotation_euler.z, yaw, abs_tol=1e-4), (name, horse.rotation_euler.z)

triangles = 0
mesh_objects = 0
for obj in bpy.data.objects:
    if obj.type == "MESH":
        mesh_objects += 1
        triangles += sum(max(1, len(poly.vertices) - 2) for poly in obj.data.polygons)

print("VERIFY_V4_OK")
print("VERSION", scene.get("version"))
print("PACKED_MAPS", sorted(found_maps))
print("BRONZE_MATERIALS_WITH_MICRO_BUMP", len(bronze_materials))
print("MESH_OBJECTS", mesh_objects)
print("TRIANGLES", triangles)
