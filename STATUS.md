# Status of the previous attempt (2026-10-25, stopped mid-way when the user moved Blender work out)

Use these as a head start, not as truth: every script below was written on another host and is only partly verified.

## A. Cast (briefs/w6-cast.md)
- `tool/room_seam_check.py`: done, pure python (struct + json). Counts UV-seam groups in the front-face zone (normal z > 0.3, |x - centre| < 30% of half width, above 45% of height). Exit 1 if any.
  - Today's GLBs: piyo 446, mongsil 175, popo 285, nuri 123, moa 277. All FAIL, which is the bug the user sees: a vertical shading line down Piyo's face on the phone (three.js mipmaps + derivative-tangent normal mapping across the Meshy UV island seam).
- `tool/room_cast_build.py`: written, NEVER RUN. Data-driven per character: retopo (QuadriFlow), seam plan, unwrap, bake, rig, clips, export, re-import check, renders.
  - Unverified risks:
    - QuadriFlow may lose the beak and eye shapes.
    - `plan_seams` may still put a seam on the face.
    - Clip rotation signs and bone positions were set by eye from grid renders.
    - `verify()` resets the scene before later renders.
    - One `vis` term in the visibility formula has no effect.
- Sources:
  - The friends' retex sources are 2K textures, 12–14k tris, with 6–64 non-manifold edges.
  - Moa's walk GLB has a 4K texture and the same UV atlas as today's moa.glb (median UV error 2e-4), so the bake is old-UV → new-UV on the same mesh.
- Decisions already made by the project owner (main):
  - Moa keeps its 6 Meshy clips (idle, walk, wave, dance, jump, sway) and gains Blender `happy` + `kick`.
  - Moa starts from today's moa.glb: no retopo, re-UV, bake old UV → new UV.
  - Popo has only front/back sheets.
  - Nuri: rig in Blender like the other friends (ignore its Meshy rig) for one consistent clip set.
- Reference render: `reviews/20261025/room/cast-rig/before-grid-front-side.jpg`.

## B. Env (briefs/w4-env.md)
- `tool/room_env_build.py`: runs in about 70 s. It measures plate swatches, then builds:
  - sky
  - mountains
  - 12 clouds `env_cloud_01..12`
  - 32 hills
  - bushes
  - terrain
  
  It then runs 3 colour-correction passes from a plate camera and exports.
- `check` mode re-imports the GLB into a fresh Blender and renders sheets.
  - Its JOB json key `repo` = absolute path of `repo/`; see `pipeline/room-env.sh` for how the job is built.
- Draft output: `assets/room/scoop/set/env.glb` (4.97 MB) + `env.json`; half-res renders in `reviews/20261025/room/env/`.
- Passed: node names; 12 cloud children; flat zone (12 samples, y 0); WebP textures; no cameras or lights; attributes COLOR_0, NORMAL, POSITION, TEXCOORD_0.
- FAILED: 152,509 triangles > 150k, so the re-import check returned rc 3.
- Colour table: hills, clouds, bushes and icing match within distance 3. These still fail:
  - sky-horizon/haze 97: cloud 05 covers the plate sample box.
  - lawn 11–15: the correction pass does not converge.
  - sky-mid 11: the floating island leaks into the sky sample strip at x 955–995.
  - mountain: not measured, because no pixels are visible.
- Fix list:
  1. Sample the sky strip from `plate-v4-noisland.png`. It differs from plate-v4 only in x 981–1061, y 268–362.
  2. Clouds read as marshmallow pillars, and the soft-serve swirl is a thin corkscrew. Rebuild them as cumulus puffs with a fat swirl. Raise the front cloud bases by +1–2° so the mountains show. Drop cloud 05.
  3. The terrain relief reaches 3.8 m, taller than the 3.4 m eye height, so it hides the hills. Cap it at about 2 m.
  4. Bushes are too big and too close. Use size 1–2.2 m at 30–65 m distance, with visible broccoli-like clumps.
  5. The lawn texture reads as speckle noise. Cap contrast at 1.3 and use soft clumps.
  6. Cut sky segments until the total is under 150k tris.
  7. The 360° sheet shows a green edge at the horizon. Start the far-terrain fade to haze earlier.
- Assumptions in the draft:
  - Plate camera: eye at (0, 3.4, 12.5), vfov 40°, horizon at row 474 of 941.
  - Lighting is computed in script and baked into vertex colour and texture rather than Cycles-baked; the brief allows any method if the table passes.

## C. Set pieces (briefs/w5-set.md)
- `tool/room_setpieces_build.py`: `--swatches` and `--meta` run in plain python; other modes need Blender.
  - `SWATCH_BOXES` holds colour boxes for 20 parts; `PIECES` holds sizes, budgets and reference crops.
  - All 10 builders are written. Only tree-pink has been run.
- Built: `assets/room/scoop/set/tree-pink.glb`: 10,056 tris, 981,072 bytes (budget 1.0 MB), height 4.000 m, min y 0, centred, two 1024 px WebP textures, 1 material.
  - Also `pieces.json`, whose swatch_table is INVALID (bug 1), and `reviews/20261025/room/set-views/tree-pink.jpg`.
- Bug 1 (blocks the colour check): Blender's PNG save rewrites the id/AO map values, so ids 8, 16, … came back as 1, 2, 4, 6, 9 and the table is wrong (canopy-pink distance 167).
  - Planned fix: write the PNGs with your own encoder (or EXR / raw float), load them back as file images, export from those. Then check whether the albedo inside the GLB has the same shift.
- Bug 2 (looks), compared with the plate:
  - The canopies read dusty pink and grey-sage instead of bright pink, and are not fluffy enough.
  - The trunk is too long and plain; it should be braided with white dots.
  - The flowers are too small.
  - The mint balls are too dark.
- Not run: the other 9 pieces, `lineup.jpg`, the determinism re-run.
