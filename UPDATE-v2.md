# UPDATE v2 (2026-10-26): read this before you continue

You started from kit v1 (2026-10-25, zip sha256 `ebe9c50d4d25085037bacd581a0d1db29986f2b6c7f9072ce73fe81c32c53838`). Since then the owner changed the locked art. Move to v2 and re-check your work against it. Where this file and START-HERE.md differ, this file wins.

## 1. Move to v2 without losing your work
1. Keep your v1 folder as it is. Put v2 in a NEW folder next to it.
2. In v1, list what you made or changed: `git status --porcelain`, or compare the files against v1's MANIFEST.txt.
3. Copy your scripts and outputs into the v2 `repo/` at the same paths. Then judge each one against §2:
   - keep what still matches;
   - redo what does not;
   - write in REPORT.md which you kept and why.
4. `CHANGES.txt` lists every file that was ADDED, CHANGED or REMOVED compared with v1.

## 2. What changed, and what it means for the 3D work

### a. Moa wears Sparkle Goggles now (the biggest change)
- The new locked sheet is `out/shorts/ep01/pack/character-moa-goggles-sheet.png`. It replaces `character-moa-sheet.png`, which is superseded: do not model from it.
- Close-ups:
  - `out/shorts/ep01/cast/goggles/goggle-A-ref.png`
  - `moa-goggles-sheet.png` (turnaround, poses, expressions)
  - `nb-turn.png`
  
  Text: `docs/shorts/heroes/GOGGLES-LOOK.md` (design A) and `docs/shorts/bible/moa-hero-mode.md`.
- The look, verbatim from GOGGLES-LOOK.md: "A pair of chunky round toy goggles rests on the top front of her cream beret, just above the teal band and never over her eyes: two round lenses with thick, soft glossy orange rims, clear glassy lenses with a faint pink-gold sheen, joined by a short orange bridge, held by a teal strap that wraps around the beret. The goggles are the only thing on the beret: no starfish clip, no pin, no other ornament. On the teal strap, at her left temple, sit three tiny five-point star lights in a row."
  - Unlit stars are soft matte grey. A lit star is warm glowing gold.
  - Everything else is unchanged: pink body, cream belly, teal neckerchief, white round tail.
- In 3D:
  - Make the goggles their own mesh `moa_goggles` (rims + bridge + lenses), rigidly parented to the head bone so that a later clip can pull them down over the eyes.
  - Make the strap part of the beret band, with the 3 stars as separate small meshes `moa_star_1..3` so the runtime can light them. Give them material `moa_star`: grey albedo, with an emissive colour slot it can turn gold.
  - Give the lenses their own material `moa_lens`: clear, faint pink-gold, glossy, roughness about 0.15. If transparency costs too much, use a bright pink-gold sheen instead.
  - Remove any starfish clip.
  - Keep Moa within 4 MB and 20k triangles; the goggles plus stars may take at most 1.5k triangles.
- Optional, only after every required clip passes: a clip `goggles_on`. In it the stars light one after another, then the goggles slide down over the eyes and the lenses glow.

### b. Material rule (new, applies to every character and object)
From `docs/shorts/bible/cast.json`, `material`:
- Characters: "smooth soft-touch toy surface, continuous even colour and broad gentle satin highlights". No fur strands, no fuzz noise, no felt.
- Objects and sets: "soft clay-toy with a smooth, softly polished surface".

In 3D:
- Bake the albedo smooth: remove the high-frequency fur and noise that the Meshy sources carry, and keep the sheet's colour areas, eyes and mouth crisp.
- Roughness: about 0.55–0.7 for characters, 0.6–0.75 for objects.
- Still no normal map (the face-seam rule).

### c. Book page 1 (the Scoop Sky world) was redrawn: this is the latest tone
- Tone lock: `reader/v2-20261012/classic-book/books/bo-sky-island/visual-lock.json`, which points to `art/scoop/pano-p1-sky2.webp`. The look is pastel coloured-pencil, with soft cotton-candy clouds: cream-white cores, pale pink and lilac shade, smooth gradients.
- Page-1 pieces are in `art/scoop/*.webp`:
  - panoramas `pano-p1-*`
  - floors `floor-*`
  - `p1-ridge`
  - the mailbox
  - bushes `pt-bush-*`, in bloom and in wilted states
  - box corners
- Moa page-1 frames are in `art/scoop/sheet-p1/`. They show the goggles look with the yellow watering can, and there is no flower on the can.
- Latest screens:
  - `reviews/20261026/astra-p1/p1-grid.jpg` (every beat at 844x390)
  - `reviews/workers/shadowsoft-20261026/user-phone-p1.jpg`
- In 3D:
  - Job B still follows `plate-v4.png` (unchanged) for layout: horizon, cloud bank and hill spacing. Where the two disagree on cloud shading and pastel softness, follow `pano-p1-sky2.webp`. Add `reviews/20261025/room/env/pano-match.jpg`: pano-p1-sky2 next to your render.
  - Job C bushes and flowers should read like the page-1 `pt-bush-*` pieces, with bloom as the default state. Compare them in the set-views sheets.

### d. Added for reference only
- Hero item sheets: `docs/shorts/heroes/art/item-sheets/{piyo,popo,mongsil,nuri}.jpg`. They show items the friends ALREADY own: Piyo's spoon-pinwheel in her crest, Popo's mint scarf, Mongsil's cream-cloud friends and Nuri's blunt horn. Model only what each friend's locked sheet shows; never add an item that is not on it.
- The room runtime now has play stations: `runtime_src/scoop_sky/stations.mjs` and `activities/*.mjs`, with captures in `reviews/20261025/room/stations/`. It looks clips up by these exact names:
  - wave
  - dance
  - happy
  - sing (Piyo)
  - kick (Popo, Moa)
  - count (Nuri)
  - bounce (Mongsil)
  - sway
  - jump
  - open (cottage door, optional)
  
  When a clip is missing, a procedural bob stands in, so your clips replace that fallback.

## 3. Done-when additions (on top of START-HERE §3)
- **Job A, Moa:**
  - `reviews/20261025/room/cast-rig/moa-goggles-compare.jpg` puts the sheet next to your render (front, 3/4, side and back) and shows the goggles, strap stars and beret matching. There is no starfish.
  - The nodes `moa_goggles` and `moa_star_1..3` exist, and the materials `moa_lens` and `moa_star` exist.
  - Seam check exits 0.
- **Job A, everyone:** 1024 px close-ups show a smooth satin surface with no fuzz noise, and the colour areas match the sheets.
- **Job B:** `plate-match.jpg` and `pano-match.jpg` both exist.
- **Job C:** bushes and flowers sit next to the `pt-bush-*` references in the set-views.

## 4. Hand-back
Follow START-HERE §5, with two changes:
- Name the zip `stargarden-room-3d-result-v2.zip`.
- In REPORT.md, add a section "Kept from v1 / redone for v2".
