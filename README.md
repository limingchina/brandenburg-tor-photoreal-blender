# Brandenburg Gate Quadriga — Blender study

A reference-guided Blender scene of the Brandenburg Gate and its quadriga, with a shared PBR texture atlas for the architectural stone and patinated bronze.

![Full gate preview](scene/brandenburg_tor_photoreal_v5_preview.png)

![Quadriga close-up](scene/brandenburg_tor_photoreal_v5_quadriga_closeup.png)

![Quadriga three-quarter view](scene/brandenburg_tor_photoreal_v5_quadriga_profile.png)

## Main file

Open `scene/brandenburg_tor_photoreal_v5.blend` in Blender 5.2 or newer. The v4 atlas images are packed into the v5 `.blend`; copies are also included in `textures/` for inspection or reuse.

The v4 scene adds a photo-informed 2K four-channel PBR atlas, metric wrapped texture coordinates, and a dedicated cast-bronze micro-pitting bump layer. V5 fixes the imported quaternion-root issue and applies a verified 15.5-degree outward yaw to the outer horses, with harness endpoints following the new pose. Each horse now also has recessed oxidized eyes, sculpted eyelid rims, tapered outer-ear shells, and darker inset ear surfaces. It retains the four linked high-detail horse meshes, modeled chariot, layered drapery and wing feathers for Victoria, and wreath/cross/eagle standard.

## Repository layout

- `scene/` — Blender scenes and rendered previews
- `textures/` — v3 1K and v4 2K albedo, metallic, normal and roughness atlas maps, plus generated source surfaces
- `assets/` — the horse source mesh used by the v3 scene
- `references/` — public-domain photographs used for material calibration
- `scripts/` — scene generation, quadriga/material upgrades and verification scripts
- `CREDITS.txt` — source and reference notes

The scripts retain the original Windows workspace paths used to generate the deliverable. The finished `.blend` is the portable artifact.

## Asset and reference notes

The horse source is “Riding Horse Trotting” from [Farm and Working Animals HD](https://3dassets.dev/packs/farm-and-working-animals-hd), released under CC0 1.0 Universal. The supplied photographs were used as visual references only.

The v4 seamless surface sources were generated with OpenAI image generation and calibrated against two public-domain Wikimedia Commons photographs. They were converted locally into the packed PBR atlas; the original photos were not perspective-projected onto the mesh. Full attribution and provenance are in `CREDITS.txt`.

Architectural proportions and detail were also informed by [Klotzkette/isometric-berlin](https://github.com/Klotzkette/isometric-berlin).
