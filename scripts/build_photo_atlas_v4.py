import bpy
import os
import numpy as np


ROOT = r"C:\Users\china\Documents\Codex\2026-09-13\can"
OUT = os.path.join(ROOT, "outputs")
SOURCES = os.path.join(ROOT, "work", "texture_sources")
SIZE = 2048
Q = SIZE // 2


def read_square(path, size):
    image = bpy.data.images.load(path, check_existing=False)
    image.scale(size, size)
    pixels = np.empty(size * size * 4, dtype=np.float32)
    image.pixels.foreach_get(pixels)
    rgba = pixels.reshape((size, size, 4)).copy()
    bpy.data.images.remove(image)
    return rgba[:, :, :3]


def soften_wrap_edges(rgb, band=96):
    """Feather opposite edges toward the same values for clean atlas tiling."""
    result = rgb.copy()
    for i in range(band):
        t = (1.0 - i / band) ** 2 * 0.52
        pair = (result[:, i, :] + result[:, -1 - i, :]) * 0.5
        result[:, i, :] = result[:, i, :] * (1.0 - t) + pair * t
        result[:, -1 - i, :] = result[:, -1 - i, :] * (1.0 - t) + pair * t
        pair = (result[i, :, :] + result[-1 - i, :, :]) * 0.5
        result[i, :, :] = result[i, :, :] * (1.0 - t) + pair * t
        result[-1 - i, :, :] = result[-1 - i, :, :] * (1.0 - t) + pair * t
    return result


def blur_wrap(gray, passes=5):
    blurred = gray.copy()
    for _ in range(passes):
        blurred = (
            blurred * 4.0
            + np.roll(blurred, 1, 0)
            + np.roll(blurred, -1, 0)
            + np.roll(blurred, 1, 1)
            + np.roll(blurred, -1, 1)
        ) / 8.0
    return blurred


def luma(rgb):
    return rgb[:, :, 0] * 0.2126 + rgb[:, :, 1] * 0.7152 + rgb[:, :, 2] * 0.0722


stone = soften_wrap_edges(read_square(os.path.join(SOURCES, "brandenburg_sandstone_source_v1.png"), Q))
bronze = soften_wrap_edges(read_square(os.path.join(SOURCES, "brandenburg_bronze_patina_source_v1.png"), Q))

# Break up any camera-oriented streaks from the generated source so the material
# remains believable on curved surfaces and on differently oriented stone blocks.
stone = stone * 0.56 + np.rot90(stone, 1) * 0.24 + np.rot90(stone, 3) * 0.20
bronze = bronze * 0.58 + np.rot90(bronze, 1) * 0.23 + np.rot90(bronze, 3) * 0.19

# Match the pale, relatively low-saturation stone seen in the public-domain facade photo.
stone_luma = luma(stone)[:, :, None]
stone = stone_luma + (stone - stone_luma) * 0.66
stone = np.clip(stone * np.array([1.035, 1.015, 0.965])[None, None, :] + 0.025, 0.0, 1.0)

# A darker, sootier companion quadrant for reliefs and sheltered recesses.
relief = np.clip(stone * np.array([0.80, 0.79, 0.76])[None, None, :] + np.array([0.018, 0.014, 0.009]), 0.0, 1.0)

# Preserve turquoise deposits while pulling the overall bronze toward the Gate's dark green.
bronze = np.clip(bronze * np.array([1.02, 1.09, 1.04])[None, None, :] + np.array([0.012, 0.020, 0.014]), 0.0, 1.0)
bronze_dark = np.clip(bronze * np.array([0.72, 0.77, 0.73])[None, None, :] + np.array([0.008, 0.014, 0.010]), 0.0, 1.0)

albedo = np.zeros((SIZE, SIZE, 3), dtype=np.float32)
albedo[:Q, :Q] = stone
albedo[:Q, Q:] = relief
albedo[Q:, :Q] = bronze
albedo[Q:, Q:] = bronze_dark

roughness = np.zeros((SIZE, SIZE), dtype=np.float32)
metallic = np.zeros((SIZE, SIZE), dtype=np.float32)
height = np.zeros((SIZE, SIZE), dtype=np.float32)

for tile, ys, xs, kind in (
    (stone, slice(0, Q), slice(0, Q), "stone"),
    (relief, slice(0, Q), slice(Q, SIZE), "relief"),
    (bronze, slice(Q, SIZE), slice(0, Q), "bronze"),
    (bronze_dark, slice(Q, SIZE), slice(Q, SIZE), "bronze_dark"),
):
    lum = luma(tile)
    broad = blur_wrap(lum, 13)
    fine = lum - blur_wrap(lum, 2)
    if kind in {"stone", "relief"}:
        base_rough = 0.74 if kind == "stone" else 0.80
        roughness[ys, xs] = np.clip(base_rough - fine * 0.75 + (0.56 - broad) * 0.10, 0.58, 0.93)
        metallic[ys, xs] = 0.0
        height[ys, xs] = np.clip(0.50 + fine * 1.25 + (broad - 0.50) * 0.16, 0.10, 0.90)
    else:
        # Pale turquoise corrosion is rougher and less electrically metallic than dark intact bronze.
        green_bias = np.clip(tile[:, :, 1] - (tile[:, :, 0] + tile[:, :, 2]) * 0.45, 0.0, 0.55)
        base_rough = 0.49 if kind == "bronze" else 0.57
        roughness[ys, xs] = np.clip(base_rough + green_bias * 0.42 - fine * 0.20, 0.38, 0.78)
        metallic[ys, xs] = np.clip(0.82 - green_bias * 0.75, 0.34, 0.82)
        rng = np.random.default_rng(1791 if kind == "bronze" else 1792)
        pits = (rng.random((Q, Q)) > 0.988).astype(np.float32)
        pits = blur_wrap(pits, 1)
        height[ys, xs] = np.clip(0.50 + fine * 1.08 + (broad - 0.32) * 0.12 - pits * 0.32, 0.10, 0.90)

gy, gx = np.gradient(height)
normal_strength = 7.4
nx = -gx * normal_strength
ny = -gy * normal_strength
nz = np.ones_like(nx)
norm = np.sqrt(nx * nx + ny * ny + nz * nz)
normal = np.dstack(((nx / norm + 1.0) * 0.5, (ny / norm + 1.0) * 0.5, (nz / norm + 1.0) * 0.5))


def save_png(name, rgb, colorspace):
    path = os.path.join(OUT, name)
    image = bpy.data.images.new(name, width=SIZE, height=SIZE, alpha=True)
    image.colorspace_settings.name = colorspace
    rgba = np.empty((SIZE, SIZE, 4), dtype=np.float32)
    rgba[:, :, :3] = np.clip(rgb, 0.0, 1.0)
    rgba[:, :, 3] = 1.0
    # Direct assignment is slower but reliably persists pixels in Blender 5.2.
    image.pixels = rgba.ravel().tolist()
    image.filepath_raw = path
    image.file_format = "PNG"
    image.save()
    bpy.data.images.remove(image)
    print("WROTE", path)


os.makedirs(OUT, exist_ok=True)
save_png("brandenburg_v4_atlas_albedo_2k.png", albedo, "sRGB")
save_png("brandenburg_v4_atlas_roughness_2k.png", np.repeat(roughness[:, :, None], 3, axis=2), "Non-Color")
save_png("brandenburg_v4_atlas_normal_2k.png", normal, "Non-Color")
save_png("brandenburg_v4_atlas_metallic_2k.png", np.repeat(metallic[:, :, None], 3, axis=2), "Non-Color")

print("ATLAS_COMPLETE", SIZE, SIZE)
