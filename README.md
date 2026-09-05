# Eye & Face Asset — photoreal eye close-up with procedural blink rig (Blender 5.2, Cycles)

A ready-to-use macro eye/face setup: scanned human head + procedural rigged eye,
with a **procedural eyelid blink** (shape key + solvers), **eyelash follow**,
**physically based skin shader** (SSS, pores, oil sheen), **tear meniscus** and
**peach fuzz**. Open `eye_face_asset.blend` and press Render.

| open (frame 40) | closed (frame 1) |
|---|---|
| ![](preview_open.png) | ![](preview_closed.png) |

## What's inside
- `MetaHumanHead_Textured` — scanned head, 2K diffuse packed, skin shader v2
- `Eyeball` + `Realistic Rigged Procedural Eye` — procedural iris/cornea rig
  (shape keys: Pupil, Dilation, Slit …), eye_aim empty for gaze
- `lashes_upper` / `lashes_lower` — geometry lashes (NURBS + bevel, no particles)
  following the lids via `lash_pivot` / `lash_pivot_lower` (CHILD_OF constraints,
  driven by the blink value)
- `TearLine` — wet meniscus tube along the lower lid margin
- `PeachFuzz` particle hair (22k, 0.5 mm) in `fuzz_zone`
- Camera `hero_socket` (macro, animated push-in), 1080×1920, 30 fps, 1–112 frames

## Blink rig (how to animate)
Shape key **`blink_close`** on the head (0 = open, 1 = closed). Everything else follows:
- `blink_arc` — in-between key (arc correction), driven by `4*v*(1-v)`
- upper/lower lashes rotate with the lid (drivers on the pivots)
- Bell's phenomenon: eyeball rolls up when closed (`delta_rotation` driver), recesses 1.5 mm
- Modifiers `LidRelax` (Corrective Smooth) + `LidContact` (Shrinkwrap to eyeball)
  keep the lid draped on the eyeball at every value

Keyframe `blink_close` only. The included curve: heavy opening → flutter blink (fr 15–16) → open by fr 28.

## Skin shader notes
SSS random-walk, radius (1.0, 0.38, 0.19) × 3.7 mm, IOR 1.40, spec 0.55,
coat 0.06/0.28 (oil), roughness = albedo×0.72 + noise, micro bump = Voronoi pores
(2600/m) + fine noise wrinkles, redness mask near the lid margins.

## Reuse in your own project
- **Append**: File → Append → `eye_face_asset.blend` → Collection (or the objects
  listed above; keep the head + eye + pivots + TearLine together — drivers reference them).
- Or **link** the whole scene and override.
- Blender **5.2** (slotted actions: drivers/keys live in
  `action.layers[0].strips[0].channelbag(slot)`). Older Blender will not read the animation.

`scripts/` contains the build scripts used to generate the rig (reference; not needed to use the asset).

## Credits & licenses
- Head: BlenderKit "3D Scanned Human Head" (free, Royalty-Free license)
- Eye: BlenderKit "Realistic Rigged Procedural Eye" by Joshua Jennings (free, Royalty-Free)
- Blink rig, lash system, skin shader, tear line, fuzz, scripts: © Mikko Nurminen, MIT (see LICENSE)

**Note on redistribution:** the head and eye come from BlenderKit under its Royalty-Free
license, which allows use in projects but not standalone redistribution of the assets.
This repository is intended for private sharing with collaborators. If you publish
derivative work, keep the assets embedded in your project rather than re-sharing them alone.
