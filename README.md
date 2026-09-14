# Brandenburg Gate Quadriga — Blender study

A reference-guided Blender scene of the Brandenburg Gate and its quadriga, with a shared PBR texture atlas for the architectural stone and patinated bronze.

![Full gate preview](scene/brandenburg_tor_photoreal_v3_preview.png)

![Quadriga close-up](scene/brandenburg_tor_photoreal_v3_quadriga_closeup.png)

## Main file

Open `scene/brandenburg_tor_photoreal_v3.blend` in Blender 5.2 or newer. The atlas images are packed into the `.blend`; copies are also included in `textures/` for inspection or reuse.

The v3 quadriga uses four linked high-detail horse meshes, improved harnesses and reins, a modeled chariot, layered drapery and wing feathers for Victoria, and the wreath/cross/eagle standard.

## Repository layout

- `scene/` — Blender scenes and rendered previews
- `textures/` — 1k albedo, metallic, normal and roughness atlas maps
- `assets/` — the horse source mesh used by the v3 scene
- `scripts/` — scene generation, quadriga upgrade and verification scripts
- `CREDITS.txt` — source and reference notes

The scripts retain the original Windows workspace paths used to generate the deliverable. The finished `.blend` is the portable artifact.

## Asset and reference notes

The horse source is “Riding Horse Trotting” from [Farm and Working Animals HD](https://3dassets.dev/packs/farm-and-working-animals-hd), released under CC0 1.0 Universal. The supplied photographs were used as visual references only; their pixels are not included in the scene materials.

Architectural proportions and detail were also informed by [Klotzkette/isometric-berlin](https://github.com/Klotzkette/isometric-berlin).
