import bpy
import math
import os
from mathutils import Vector

ROOT = r"C:\Users\china\Documents\Codex\2026-09-13\can"
OUT = os.path.join(ROOT, "outputs")
HORSE_GLB = os.path.join(ROOT, "work", "assets", "horse_trotting.glb")
BLEND_OUT = os.path.join(OUT, "brandenburg_tor_photoreal_v3.blend")

scene = bpy.context.scene
base_bronze = bpy.data.materials.get("MAT_PBR_ATLAS_BRONZE")
base_bronze_dark = bpy.data.materials.get("MAT_PBR_ATLAS_BRONZE_DARK")
if not base_bronze or not base_bronze_dark:
    raise RuntimeError("Expected atlas bronze materials were not found in the v2 scene")


def atlas_image(filename, non_color=False):
    path = os.path.join(OUT, filename)
    image = next((im for im in bpy.data.images if bpy.path.abspath(im.filepath) == path), None)
    if image is None:
        image = bpy.data.images.load(path, check_existing=True)
    if non_color:
        image.colorspace_settings.name = "Non-Color"
    return image


def sculpture_atlas_material(name, region):
    """Use the shared PBR atlas, constrained to one bronze quadrant."""
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    mat["atlas_region"] = region
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    tc = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    mapping.vector_type = "POINT"
    u0 = .01 if region == "bronze" else .51
    v0 = .51
    mapping.inputs["Location"].default_value = (u0, v0, 0)
    mapping.inputs["Scale"].default_value = (.48, .48, 0)
    links.new(tc.outputs["Generated"], mapping.inputs["Vector"])

    albedo = nodes.new("ShaderNodeTexImage")
    albedo.image = atlas_image("brandenburg_atlas_albedo_1k.png")
    albedo.extension = "EXTEND"
    links.new(mapping.outputs["Vector"], albedo.inputs["Vector"])
    links.new(albedo.outputs["Color"], bsdf.inputs["Base Color"])

    rough_tex = nodes.new("ShaderNodeTexImage")
    rough_tex.image = atlas_image("brandenburg_atlas_roughness_1k.png", True)
    links.new(mapping.outputs["Vector"], rough_tex.inputs["Vector"])
    rough = nodes.new("ShaderNodeMath")
    rough.operation = "MULTIPLY_ADD"
    rough.inputs[1].default_value = .34
    rough.inputs[2].default_value = .39
    links.new(rough_tex.outputs["Color"], rough.inputs[0])
    links.new(rough.outputs[0], bsdf.inputs["Roughness"])

    metal_tex = nodes.new("ShaderNodeTexImage")
    metal_tex.image = atlas_image("brandenburg_atlas_metallic_1k.png", True)
    links.new(mapping.outputs["Vector"], metal_tex.inputs["Vector"])
    metal = nodes.new("ShaderNodeMath")
    metal.operation = "MULTIPLY"
    metal.inputs[1].default_value = .58
    links.new(metal_tex.outputs["Color"], metal.inputs[0])
    links.new(metal.outputs[0], bsdf.inputs["Metallic"])

    normal_tex = nodes.new("ShaderNodeTexImage")
    normal_tex.image = atlas_image("brandenburg_atlas_normal_1k.png", True)
    links.new(mapping.outputs["Vector"], normal_tex.inputs["Vector"])
    normal = nodes.new("ShaderNodeNormalMap")
    normal.inputs["Strength"].default_value = .28
    links.new(normal_tex.outputs["Color"], normal.inputs["Color"])
    links.new(normal.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


bronze = sculpture_atlas_material("MAT_ATLAS_QUADRIGA_BRONZE_V3", "bronze")
bronze_dark = sculpture_atlas_material("MAT_ATLAS_QUADRIGA_BRONZE_DARK_V3", "bronze_dark")


def delete_collection(name):
    coll = bpy.data.collections.get(name)
    if not coll:
        return
    for obj in list(coll.all_objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(coll)


delete_collection("QUADRIGA_HIGH_DETAIL")
quad = bpy.data.collections.new("QUADRIGA_REFERENCE_MATCHED")
scene.collection.children.link(quad)


def put(obj, coll=quad):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    coll.objects.link(obj)
    return obj


def assign(obj, material):
    if obj.type == "MESH":
        obj.data.materials.clear()
        obj.data.materials.append(material)
        for poly in obj.data.polygons:
            poly.use_smooth = True
    elif obj.type == "CURVE":
        obj.data.materials.clear()
        obj.data.materials.append(material)
    return obj


def box(name, loc, dims, material=bronze, bevel=0.04):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    obj = put(bpy.context.object)
    obj.name = name
    obj.scale = (dims[0] / 2, dims[1] / 2, dims[2] / 2)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    assign(obj, material)
    if bevel:
        mod = obj.modifiers.new("Sculpted edge", "BEVEL")
        mod.width = bevel
        mod.segments = 3
    return obj


def sphere(name, loc, scale, material=bronze, segments=40, rings=24):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=loc)
    obj = put(bpy.context.object)
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return assign(obj, material)


def cone(name, loc, r1, r2, depth, material=bronze, vertices=40):
    bpy.ops.mesh.primitive_cone_add(vertices=vertices, radius1=r1, radius2=r2, depth=depth, location=loc)
    obj = put(bpy.context.object)
    obj.name = name
    return assign(obj, material)


def between(name, a, b, r1, r2=None, material=bronze, vertices=24):
    if r2 is None:
        r2 = r1
    a, b = Vector(a), Vector(b)
    d = b - a
    bpy.ops.mesh.primitive_cone_add(vertices=vertices, radius1=r1, radius2=r2, depth=d.length, location=(a + b) / 2)
    obj = put(bpy.context.object)
    obj.name = name
    obj.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    return assign(obj, material)


def torus(name, loc, major, minor, material=bronze_dark, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, major_segments=64, minor_segments=16, location=loc, rotation=rot)
    obj = put(bpy.context.object)
    obj.name = name
    return assign(obj, material)


def tube(name, points, radius, material=bronze_dark, cyclic=False):
    curve = bpy.data.curves.new(name + " Curve", "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 3
    curve.bevel_resolution = 3
    curve.bevel_depth = radius
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for bp, co in zip(spline.bezier_points, points):
        bp.co = co
        bp.handle_left_type = "AUTO"
        bp.handle_right_type = "AUTO"
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, curve)
    quad.objects.link(obj)
    return assign(obj, material)


def feather(name, root, tip, width, material=bronze):
    root, tip = Vector(root), Vector(tip)
    direction = tip - root
    length = direction.length
    if length == 0:
        raise ValueError("Feather cannot have zero length")
    direction.normalize()
    # Keep feather breadth in the facade plane so each overlapping vane reads
    # clearly from the frontal reference camera.
    broad = Vector((-direction.z, 0, direction.x))
    if broad.length < 0.01:
        broad = Vector((1, 0, 0))
    broad.normalize()
    thick_axis = direction.cross(broad).normalized()
    stations = 12
    verts = []
    for i in range(stations + 1):
        t = i / stations
        profile = max(0.025, math.sin(math.pi * t) ** 0.72)
        w = width * profile * (1.06 - 0.22 * t)
        thick = width * 0.12 * profile
        center = root + direction * (length * t)
        verts.extend([center - broad * w, center - thick_axis * thick,
                      center + broad * w, center + thick_axis * thick])
    faces = []
    for i in range(stations):
        a = i * 4
        b = (i + 1) * 4
        faces.extend([(a, a + 1, b + 1, b), (a + 1, a + 2, b + 2, b + 1),
                      (a + 2, a + 3, b + 3, b + 2), (a + 3, a, b, b + 3)])
    faces.append((0, 3, 2, 1))
    e = stations * 4
    faces.append((e, e + 1, e + 2, e + 3))
    mesh = bpy.data.meshes.new(name + " Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    quad.objects.link(obj)
    assign(obj, material)
    bevel = obj.modifiers.new("Feather edge softness", "BEVEL")
    bevel.width = 0.012
    bevel.segments = 2
    return obj


def look_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


# -----------------------------------------------------------------------------
# Four linked high-fidelity horses, based on the supplied close-up silhouette.
# -----------------------------------------------------------------------------
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=HORSE_GLB)
imported = [o for o in bpy.data.objects if o not in before]
root = next((o for o in imported if o.type == "EMPTY" and o.parent is None), None)
if root is None:
    root = bpy.data.objects.new("Horse source root", None)
    quad.objects.link(root)
    for o in imported:
        if o.parent is None:
            o.parent = root
for obj in imported:
    put(obj)

root.name = "Horse 1 high fidelity"
for obj in imported:
    if obj.type != "MESH":
        continue
    old_names = [m.name.lower() for m in obj.data.materials if m]
    obj.name = "Horse 1 " + ("mane, tail and hooves" if any("dark" in n for n in old_names) else "anatomical body")
    assign(obj, bronze_dark if any("dark" in n for n in old_names) else bronze)


def clone_hierarchy(source_root, index):
    originals = [source_root] + list(source_root.children_recursive)
    copies = {o: o.copy() for o in originals}
    for old, new in copies.items():
        new.name = old.name.replace("Horse 1", f"Horse {index}")
        quad.objects.link(new)
    for old, new in copies.items():
        new.parent = copies.get(old.parent)
    return copies[source_root]


horses = [root] + [clone_hierarchy(root, i) for i in range(2, 5)]
lanes = (-1.95, -0.65, 0.65, 1.95)
angles = (-0.095, -0.026, 0.026, 0.095)
y_offsets = (-0.05, -0.20, -0.20, -0.05)
for i, (horse, x, ang, y) in enumerate(zip(horses, lanes, angles, y_offsets), 1):
    mirror = -1.0 if i in (2, 4) else 1.0
    horse.location = (x, y, 20.28 + (0.025 if i % 2 else 0.0))
    horse.rotation_euler = (0, 0, ang)
    horse.scale = (1.52 * mirror, 1.52, 1.52)
    horse["source"] = "CC0 Riding Horse Trotting, 3DAssets.dev"
    horse["reference_adjustment"] = "Mirrored/angled to reproduce Brandenburg quadriga cadence"

# Detailed harness: collars, bridles, reins, central traces, and chest straps.
for i, x in enumerate(lanes, 1):
    outer = abs(x) > 1.0
    turn = (-0.12 if x < 0 else 0.12) if outer else (-0.035 if x < 0 else 0.035)
    head_x = x + turn
    tube(f"Horse {i} browband", [(head_x - .30, -1.88, 23.10), (head_x, -2.00, 23.20), (head_x + .30, -1.88, 23.10)], .025)
    tube(f"Horse {i} noseband", [(head_x - .25, -2.20, 22.84), (head_x, -2.28, 22.91), (head_x + .25, -2.20, 22.84)], .023)
    tube(f"Horse {i} breast collar", [(x - .34, -.72, 22.15), (x, -.90, 22.48), (x + .34, -.72, 22.15)], .045, bronze_dark)
    tube(f"Horse {i} left rein", [(head_x - .15, -2.12, 22.92), (x * .78, -.40, 22.62), (x * .44, .82, 22.58), (-.18, 1.58, 23.12)], .018)
    tube(f"Horse {i} right rein", [(head_x + .15, -2.12, 22.92), (x * .88, -.35, 22.68), (x * .53, .90, 22.64), (.18, 1.58, 23.12)], .018)
    tube(f"Horse {i} trace left", [(x - .24, -.72, 21.92), (x - .28, .55, 21.55), (-.75, 1.35, 21.42)], .022)
    tube(f"Horse {i} trace right", [(x + .24, -.72, 21.92), (x + .28, .55, 21.55), (.75, 1.35, 21.42)], .022)

# -----------------------------------------------------------------------------
# Compact chariot with deeply modeled wheel/spoke and relief detail.
# -----------------------------------------------------------------------------
box("Chariot floor", (0, 1.58, 21.00), (1.95, 1.75, .19), bronze_dark, .055)
box("Chariot front breastwork", (0, .98, 21.70), (2.15, .17, 1.32), bronze, .075)
box("Chariot rear rail", (0, 2.22, 21.63), (1.75, .13, .84), bronze_dark, .045)
for sx in (-1, 1):
    box(f"Chariot side {sx}", (sx * .98, 1.60, 21.56), (.17, 1.35, 1.05), bronze, .055)
    torus(f"Chariot wheel {sx}", (sx * 1.12, 1.74, 20.96), .82, .085, bronze_dark, (0, math.pi / 2, 0))
    between(f"Wheel axle {sx}", (sx * .96, 1.74, 20.96), (sx * 1.26, 1.74, 20.96), .14, .14, bronze_dark, 32)
    for j in range(14):
        a = 2 * math.pi * j / 14
        between(f"Wheel {sx} spoke {j}", (sx * 1.14, 1.74, 20.96),
                (sx * 1.14, 1.74 + .72 * math.cos(a), 20.96 + .72 * math.sin(a)), .024, .017, bronze, 12)
for j in range(9):
    x = -.82 + j * .205
    sphere(f"Chariot front relief boss {j}", (x, .875, 21.70), (.07, .028, .28), bronze_dark, 18, 10)
tube("Draught pole", [(0, 1.50, 20.94), (0, .15, 21.10), (0, -1.65, 21.42)], .055)

# -----------------------------------------------------------------------------
# Victoria: continuous anatomical core, layered drapery, face, hair and wings.
# -----------------------------------------------------------------------------
body_parts = []


def body_s(loc, scale):
    body_parts.append(sphere("Victoria temporary anatomy", loc, scale, bronze, 36, 22))


def body_b(a, b, r1, r2):
    body_parts.append(between("Victoria temporary anatomy", a, b, r1, r2, bronze, 28))


body_s((0, 1.65, 22.88), (.32, .23, .46))
body_s((0, 1.65, 22.47), (.30, .24, .32))
body_b((0, 1.64, 23.22), (0, 1.63, 23.38), .115, .10)
body_s((0, 1.62, 23.60), (.225, .205, .275))
body_s((0, 1.50, 23.48), (.17, .12, .18))  # jaw and lower face
body_b((-.24, 1.63, 23.05), (-.53, 1.36, 23.22), .115, .085)
body_b((-.53, 1.36, 23.22), (-.25, .93, 23.30), .085, .055)
body_b((.24, 1.63, 23.06), (.50, 1.35, 23.27), .115, .085)
body_b((.50, 1.35, 23.27), (.29, .92, 23.70), .085, .055)

bpy.ops.object.select_all(action="DESELECT")
for p in body_parts:
    p.select_set(True)
bpy.context.view_layer.objects.active = body_parts[0]
bpy.ops.object.join()
victoria = bpy.context.object
victoria.name = "Victoria continuous anatomical sculpture"
try:
    victoria.data.remesh_voxel_size = .032
    victoria.data.remesh_voxel_adaptivity = 0.0
    bpy.ops.object.voxel_remesh()
except Exception as exc:
    print("Victoria remesh fallback", exc)
assign(victoria, bronze)
sub = victoria.modifiers.new("Victoria sculpt subdivision", "SUBSURF")
sub.levels = 1
sub.render_levels = 1

# Drapery is built in layers, with asymmetrical wind-swept folds visible in the photo.
cone("Victoria lower robe", (0, 1.70, 21.98), .53, .25, 1.72, bronze, 64)
cone("Victoria upper robe", (0, 1.67, 22.62), .35, .27, .88, bronze, 56)
for j in range(18):
    a = 2 * math.pi * j / 18
    x = .23 * math.cos(a)
    y = 1.67 + .15 * math.sin(a)
    sway = .10 * math.sin(j * 1.7)
    tube(f"Victoria robe fold {j}", [(x, y, 22.92), (x * 1.35 + sway, y + .02, 22.22),
                                      (x * 1.75 + sway * 1.6, y + .04, 21.22)], .026 if j % 2 else .035,
         bronze_dark if j % 3 == 0 else bronze)
tube("Victoria wind-swept mantle", [(-.27, 1.75, 23.16), (-.62, 1.95, 22.92), (-.82, 2.18, 22.34), (-.70, 2.27, 21.82)], .075, bronze)

# Face and coiffure details.
between("Victoria nose", (0, 1.405, 23.63), (0, 1.285, 23.59), .048, .015, bronze, 18)
sphere("Victoria chin", (0, 1.43, 23.43), (.105, .075, .07), bronze, 24, 14)
for sx in (-1, 1):
    sphere(f"Victoria eye {sx}", (sx * .082, 1.405, 23.66), (.032, .022, .024), bronze_dark, 16, 10)
    sphere(f"Victoria ear {sx}", (sx * .215, 1.62, 23.60), (.042, .026, .065), bronze, 16, 10)
for j in range(16):
    a = 2 * math.pi * j / 16
    sphere(f"Victoria hair curl {j}", (.19 * math.cos(a), 1.69 + .12 * math.sin(a), 23.76 + .10 * math.sin(a * 2)),
           (.075, .065, .075), bronze_dark, 18, 12)

# Wing bones and three overlapping feather ranks per side.
for side in (-1, 1):
    between(f"Victoria wing shoulder {side}", (side * .18, 1.73, 23.06), (side * .58, 1.78, 23.50), .145, .095, bronze, 28)
    between(f"Victoria wing spar {side}", (side * .55, 1.78, 23.46), (side * 1.42, 1.86, 24.33), .10, .045, bronze, 24)
    # Long primaries form the open wing silhouette.
    for j in range(15):
        t = j / 14
        root_pt = (side * (.48 + .67 * t), 1.82 + .05 * t, 23.48 + .54 * t)
        tip_pt = (side * (.84 + 1.12 * t), 1.94 + .025 * j, 23.30 + .80 * t - .18 * t * t)
        feather(f"Victoria primary feather {side}:{j}", root_pt, tip_pt, .105 - .025 * t,
                bronze_dark if j % 3 == 0 else bronze)
    for j in range(12):
        t = j / 11
        root_pt = (side * (.31 + .55 * t), 1.79, 23.34 + .50 * t)
        tip_pt = (side * (.64 + .87 * t), 1.88 + .018 * j, 23.55 + .72 * t)
        feather(f"Victoria secondary feather {side}:{j}", root_pt, tip_pt, .115 - .03 * t, bronze)
    for j in range(9):
        t = j / 8
        root_pt = (side * (.22 + .39 * t), 1.75, 23.18 + .41 * t)
        tip_pt = (side * (.48 + .60 * t), 1.83, 23.45 + .57 * t)
        feather(f"Victoria covert feather {side}:{j}", root_pt, tip_pt, .105, bronze_dark if j % 2 else bronze)

# Standard, wreath, Iron Cross, and eagle crest.
between("Victoria standard staff", (.29, .91, 23.68), (.29, .88, 25.42), .040, .032, bronze_dark, 20)
torus("Victoria oak wreath", (.29, .82, 25.08), .36, .047, bronze, (math.pi / 2, 0, 0))
for j in range(26):
    a = 2 * math.pi * j / 26
    sphere(f"Oak leaf {j}", (.29 + .31 * math.cos(a), .77, 25.08 + .31 * math.sin(a)), (.082, .024, .045),
           bronze if j % 2 else bronze_dark, 16, 10)

pts = [(-.10, .40), (.10, .40), (.145, .145), (.40, .10), (.40, -.10), (.145, -.145),
       (.10, -.40), (-.10, -.40), (-.145, -.145), (-.40, -.10), (-.40, .10), (-.145, .145)]
cross_curve = bpy.data.curves.new("Iron Cross Shape v3", "CURVE")
cross_curve.dimensions = "2D"
cross_curve.extrude = .045
cross_curve.bevel_depth = .010
sp = cross_curve.splines.new("POLY")
sp.points.add(len(pts) - 1)
for p, (px, pz) in zip(sp.points, pts):
    p.co = (px, pz, 0, 1)
sp.use_cyclic_u = True
cross = bpy.data.objects.new("Iron Cross v3", cross_curve)
quad.objects.link(cross)
cross.location = (.29, .74, 25.08)
cross.rotation_euler = (math.pi / 2, 0, 0)
assign(cross, bronze_dark)

sphere("Prussian eagle torso", (.29, .89, 25.57), (.17, .12, .24), bronze, 30, 18)
sphere("Prussian eagle head", (.29, .81, 25.79), (.11, .10, .115), bronze, 24, 14)
between("Prussian eagle beak", (.29, .72, 25.80), (.29, .60, 25.78), .050, .006, bronze_dark, 16)
for side in (-1, 1):
    between(f"Eagle wing spar {side}", (.29 + side * .08, .90, 25.65), (.29 + side * .42, .91, 25.82), .065, .028, bronze, 18)
    for j in range(7):
        feather(f"Eagle flight feather {side}:{j}", (.29 + side * (.10 + .035 * j), .91, 25.66 + .025 * j),
                (.29 + side * (.36 + .09 * j), .92, 25.84 - .025 * j), .045, bronze if j % 2 else bronze_dark)

# Photo-aligned close-up camera and render settings.
qcam = bpy.data.objects.get("CAM_Quadriga_Closeup")
main_cam = bpy.data.objects.get("CAM_Main_Photoreal")
qfocus = bpy.data.objects.get("Quadriga focus target")
if qfocus:
    qfocus.location = (0, -.20, 23.10)
if qcam:
    qcam.location = (5.2, -31.5, 25.65)
    qcam.data.lens = 78
    qcam.data.sensor_width = 36
    qcam.data.dof.aperture_fstop = 9
    look_at(qcam, (0, -.20, 23.08))

scene.render.engine = "BLENDER_EEVEE"
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.resolution_percentage = 100
scene.view_settings.look = "AgX - Medium High Contrast"
scene["asset_name"] = "Brandenburg Tor Photoreal V3"
scene["quadriga_geometry"] = "Four linked 20.5k-triangle CC0 anatomical horses; reference-matched chariot, harness, Victoria and layered wings"
scene["quadriga_reference"] = "User-supplied close-up photograph used for silhouette and proportion reference only"
scene["horse_source"] = "Farm and Working Animals HD / Riding Horse Trotting, CC0 1.0, 3DAssets.dev"
scene["atlas_pack"] = "brandenburg_atlas_{albedo,roughness,normal,metallic}_1k.png"

bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT)

if main_cam:
    scene.camera = main_cam
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.filepath = os.path.join(OUT, "brandenburg_tor_photoreal_v3_preview.png")
    bpy.ops.render.render(write_still=True)

if qcam:
    scene.camera = qcam
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 900
    scene.render.filepath = os.path.join(OUT, "brandenburg_tor_photoreal_v3_quadriga_closeup.png")
    bpy.ops.render.render(write_still=True)

if main_cam:
    scene.camera = main_cam
bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT)

credits = os.path.join(OUT, "brandenburg_tor_photoreal_v3_CREDITS.txt")
with open(credits, "w", encoding="utf-8") as f:
    f.write("Brandenburg Tor Photoreal V3\n\n")
    f.write("The two user-supplied photographs were used as visual references only.\n")
    f.write("High-detail horse geometry: Riding Horse Trotting from Farm and Working Animals HD, CC0 1.0 Universal, 3DAssets.dev.\n")
    f.write("https://3dassets.dev/packs/farm-and-working-animals-hd\n")
    f.write("Metric/detail reference: Klotzkette/isometric-berlin, MIT License.\n")
    f.write("https://github.com/Klotzkette/isometric-berlin\n")

print("V3_COMPLETE", BLEND_OUT)
