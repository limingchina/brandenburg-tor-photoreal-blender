import bpy
import os
from mathutils import Vector


ROOT = r"C:\Users\china\Documents\Codex\2026-09-13\can"
OUT = os.path.join(ROOT, "outputs")
BLEND_OUT = os.path.join(OUT, "brandenburg_tor_photoreal_v4.blend")

MAPS = {
    "albedo": "brandenburg_v4_atlas_albedo_2k.png",
    "roughness": "brandenburg_v4_atlas_roughness_2k.png",
    "normal": "brandenburg_v4_atlas_normal_2k.png",
    "metallic": "brandenburg_v4_atlas_metallic_2k.png",
}


def load_map(kind):
    path = os.path.join(OUT, MAPS[kind])
    image = bpy.data.images.load(path, check_existing=True)
    image.name = MAPS[kind]
    image.colorspace_settings.name = "sRGB" if kind == "albedo" else "Non-Color"
    return image


images = {kind: load_map(kind) for kind in MAPS}

# Reference-matched quadriga fan: the outer pair open away from the centerline,
# while the inner pair retain a nearly forward cadence.
horse_layout = {
    "Horse 1 high fidelity": (-2.08, 0.02, -0.205),
    "Horse 2 high fidelity": (-0.68, -0.20, -0.040),
    "Horse 3 high fidelity": (0.68, -0.20, 0.040),
    "Horse 4 high fidelity": (2.08, 0.02, 0.205),
}
for horse_name, (x, y, yaw) in horse_layout.items():
    horse = bpy.data.objects.get(horse_name)
    if horse:
        horse.location.x = x
        horse.location.y = y
        horse.rotation_euler.z = yaw
        horse["v4_formation"] = "Outer pair widened and yawed outward from public-domain frontal reference"


def image_kind(node):
    words = " ".join((node.name, node.label, node.image.name if node.image else "")).lower()
    if "albedo" in words or "basecolor" in words or "base_color" in words:
        return "albedo"
    if "rough" in words:
        return "roughness"
    if "normal" in words:
        return "normal"
    if "metal" in words:
        return "metallic"
    return None


updated_materials = []
for material in bpy.data.materials:
    region = material.get("atlas_region")
    if not material.use_nodes or region not in {"stone", "relief", "bronze", "bronze_dark"}:
        continue
    updated_materials.append(material.name)
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    for node in nodes:
        if node.bl_idname != "ShaderNodeTexImage":
            continue
        kind = image_kind(node)
        if kind:
            node.image = images[kind]
            node.interpolation = "Smart"
            node.extension = "EXTEND"

    # Replace normalized Generated mapping with local metric coordinates, wrapped
    # inside the assigned atlas quadrant. This prevents long facade pieces from
    # stretching a single texture sample into visible vertical bands.
    texcoord = next((n for n in nodes if n.bl_idname == "ShaderNodeTexCoord"), None)
    mapping = next((n for n in nodes if n.bl_idname == "ShaderNodeMapping"), None)
    if texcoord and mapping:
        for link in list(mapping.inputs["Vector"].links):
            links.remove(link)
        scale = nodes.get("V4 metric texture scale") or nodes.new("ShaderNodeVectorMath")
        scale.name = "V4 metric texture scale"
        scale.operation = "SCALE"
        scale.inputs["Scale"].default_value = 0.78 if region in {"stone", "relief"} else 0.92
        fract = nodes.get("V4 atlas wrap") or nodes.new("ShaderNodeVectorMath")
        fract.name = "V4 atlas wrap"
        fract.operation = "FRACTION"
        links.new(texcoord.outputs["Object"], scale.inputs[0])
        links.new(scale.outputs["Vector"], fract.inputs[0])
        links.new(fract.outputs["Vector"], mapping.inputs["Vector"])
    for node in nodes:
        if node.bl_idname == "ShaderNodeNormalMap":
            node.inputs["Strength"].default_value = 0.30 if region in {"stone", "relief"} else 0.68
        elif node.bl_idname == "ShaderNodeBsdfPrincipled":
            if "IOR" in node.inputs:
                node.inputs["IOR"].default_value = 1.48
            if "Coat Weight" in node.inputs:
                node.inputs["Coat Weight"].default_value = 0.04 if region in {"stone", "relief"} else 0.13
            if "Coat Roughness" in node.inputs:
                node.inputs["Coat Roughness"].default_value = 0.42 if region in {"stone", "relief"} else 0.26
    # V3 sculpture materials used conservative multipliers that made bronze read as plastic.
    if region in {"bronze", "bronze_dark"}:
        for node in nodes:
            if node.bl_idname != "ShaderNodeMath":
                continue
            destinations = [link.to_socket.name for link in material.node_tree.links if link.from_node == node]
            if "Metallic" in destinations:
                node.inputs[1].default_value = 0.96
            if "Roughness" in destinations and node.operation == "MULTIPLY_ADD":
                node.inputs[1].default_value = 0.64
                node.inputs[2].default_value = 0.17

        # Fine cast-metal pitting layered over the photo-derived tangent normal.
        # It is shader-only, so the high-fidelity horse silhouettes stay untouched.
        texcoord = next((n for n in nodes if n.bl_idname == "ShaderNodeTexCoord"), None)
        normal_map = next((n for n in nodes if n.bl_idname == "ShaderNodeNormalMap"), None)
        bsdf = next((n for n in nodes if n.bl_idname == "ShaderNodeBsdfPrincipled"), None)
        if texcoord and normal_map and bsdf:
            for link in list(bsdf.inputs["Normal"].links):
                links.remove(link)
            noise = nodes.new("ShaderNodeTexNoise")
            noise.name = "V4 bronze micro-pitting"
            noise.noise_dimensions = "3D"
            noise.inputs["Scale"].default_value = 115.0
            noise.inputs["Detail"].default_value = 5.5
            noise.inputs["Roughness"].default_value = 0.82
            if "Distortion" in noise.inputs:
                noise.inputs["Distortion"].default_value = 0.14
            bump = nodes.new("ShaderNodeBump")
            bump.name = "V4 cast bronze micro-bump"
            bump.inputs["Strength"].default_value = 0.26
            bump.inputs["Distance"].default_value = 0.055
            links.new(texcoord.outputs["Object"], noise.inputs["Vector"])
            links.new(noise.outputs["Fac"], bump.inputs["Height"])
            links.new(normal_map.outputs["Normal"], bump.inputs["Normal"])
            links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])


def look_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.image_settings.color_depth = "8"
scene.render.resolution_percentage = 100
scene.render.film_transparent = False
scene.render.use_file_extension = True
scene.render.image_settings.compression = 28
scene.view_settings.look = "AgX - Medium High Contrast"

# Neutral daylight keeps the photo-derived colors legible and gives patinated metal crisp highlights.
world = scene.world
world.use_nodes = True
background = world.node_tree.nodes.get("Background")
if background:
    background.inputs["Color"].default_value = (0.34, 0.43, 0.56, 1.0)
    background.inputs["Strength"].default_value = 0.30

sun = bpy.data.objects.get("Late afternoon sun")
if sun:
    sun.data.energy = 3.0
    sun.data.angle = 0.075
    sun.rotation_euler = (0.48, -0.62, -0.72)

key = bpy.data.objects.get("Quadriga key")
if key:
    key.data.energy = 3200.0
    key.data.color = (1.0, 0.82, 0.66)
    key.data.shape = "DISK"
    key.data.size = 8.0

fill = bpy.data.objects.get("Soft facade fill")
if fill:
    fill.data.energy = 5200.0
    fill.data.color = (0.66, 0.79, 1.0)
    fill.data.size = 18.0

main_cam = bpy.data.objects.get("CAM_Main_Photoreal")
quad_cam = bpy.data.objects.get("CAM_Quadriga_Closeup")
if quad_cam:
    quad_cam.location = (1.7, -32.0, 25.2)
    quad_cam.data.lens = 82
    quad_cam.data.dof.aperture_fstop = 11
    look_at(quad_cam, (0.0, -0.25, 23.15))

facade_cam = bpy.data.objects.get("CAM_Facade_Reference")
if facade_cam is None:
    camera_data = bpy.data.cameras.new("CAM_Facade_Reference")
    facade_cam = bpy.data.objects.new("CAM_Facade_Reference", camera_data)
    scene.collection.objects.link(facade_cam)
facade_cam.location = (0.0, -105.0, 16.2)
facade_cam.data.lens = 68
facade_cam.data.sensor_width = 36
facade_cam.data.dof.use_dof = False
look_at(facade_cam, (0.0, 0.0, 11.8))

profile_cam = bpy.data.objects.get("CAM_Quadriga_Profile")
if profile_cam is None:
    profile_data = bpy.data.cameras.new("CAM_Quadriga_Profile")
    profile_cam = bpy.data.objects.new("CAM_Quadriga_Profile", profile_data)
    scene.collection.objects.link(profile_cam)
profile_cam.location = (-18.0, -20.0, 25.4)
profile_cam.data.lens = 72
profile_cam.data.sensor_width = 36
profile_cam.data.dof.use_dof = False
look_at(profile_cam, (0.0, 0.2, 23.05))

scene["version"] = "4.0 photo-derived material pass"
scene["atlas_pack"] = "brandenburg_v4_atlas_{albedo,roughness,normal,metallic}_2k.png"
scene["material_notes"] = "2K four-quadrant PBR atlas from generated seamless sources color-calibrated against public-domain Brandenburg Gate photographs."
scene["reference_policy"] = "Public-domain reference photographs used for visual calibration; no perspective photo projection."
scene["quadriga_formation"] = "Outer horses yawed 11.7 degrees outward; inner horses yawed 2.3 degrees outward."

# Discard the superseded packed procedural maps, then pack the v4 maps so the
# finished blend is portable without carrying two generations of textures.
for image in list(bpy.data.images):
    if image in images.values():
        continue
    if image.name.lower().startswith("brandenburg_atlas_") and image.users == 0:
        bpy.data.images.remove(image)

# Pack only after all material references point to the new maps.
for image in images.values():
    if not image.packed_file:
        image.pack()

bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT)

if main_cam:
    scene.camera = main_cam
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.filepath = os.path.join(OUT, "brandenburg_tor_photoreal_v4_preview.png")
    bpy.ops.render.render(write_still=True)

if quad_cam:
    scene.camera = quad_cam
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 900
    scene.render.filepath = os.path.join(OUT, "brandenburg_tor_photoreal_v4_quadriga_closeup.png")
    bpy.ops.render.render(write_still=True)

scene.camera = facade_cam
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.filepath = os.path.join(OUT, "brandenburg_tor_photoreal_v4_facade_closeup.png")
bpy.ops.render.render(write_still=True)

scene.camera = profile_cam
scene.render.resolution_x = 1200
scene.render.resolution_y = 900
scene.render.filepath = os.path.join(OUT, "brandenburg_tor_photoreal_v4_quadriga_profile.png")
bpy.ops.render.render(write_still=True)

if main_cam:
    scene.camera = main_cam
bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT)

print("UPDATED_MATERIALS", len(updated_materials), updated_materials)
print("SAVED", BLEND_OUT)
