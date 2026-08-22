# Five-style photo workflow

This is an agent workflow, not a local filter script. It deliberately uses the image-generation/editing tool required by the upstream skills.

## Input and run directory

1. Resolve the supplied photograph to an absolute path and confirm it is a readable image.
2. Inspect it with `view_image` before writing prompts. Record visible subject identity, composition, colors, text/branding, and preservation invariants.
3. Compute the first eight lowercase hex characters of the source file's SHA-256. Sanitize its filename stem to ASCII letters, digits, `_`, and `-`; use `photo` if nothing remains.
4. Create `outputs/<stem>--<sha8>/` and `.work/<stem>--<sha8>/`.
5. If that output folder already exists and passes `scripts/verify_outputs.py`, return it instead of silently regenerating. If the user explicitly requests a rerun, create the first unused `<stem>--<sha8>--rNN/` folder, beginning with `r02`.

All five variants use the same original photograph. They run serially so that each skill's inspection and quality gate is completed before the next begins, but no generated variant becomes another variant's input.

## Required order

### 1. `photo-abstract-editorial`

- Read `.agents/skills/photo-abstract-editorial/SKILL.md` and its Chinese reference prompt completely.
- Use the actual photograph as the sole content source and generate the finished adaptive photo-plus-ivory-panel editorial.
- Preserve the photographic region; derive the sparse motif, muted palette, and one exact English title only from visible source facts.
- Reject a mere filter, redrawn photograph, generic icon, textured panel, extra text, logo, or watermark. Apply the upstream visual constraints before accepting.
- Stage the accepted raster in `.work/`, then copy only the final PNG to `01-photo-abstract-editorial.png`.

### 2. `pixel-style-poster-skill`

- Read `.agents/skills/pixel-style-poster-skill/SKILL.md` completely.
- Pass the actual photograph to image generation. Translate its recognizable subject into a vertical 3:4 fine bitmap editorial print poster.
- Use fine dot-matrix or micro-pixel density, restrained ink, scanned paper, and the title/microtype policy selected from the upstream variation engine.
- Reject chunky 8-bit game art, sprites, smooth photographic effects, generic cartoon treatment, repeated text, or commercial-ad layout. Regenerate once when the upstream gate requires it.
- Save only the accepted PNG as `02-pixel-style-poster-skill.png`.

### 3. `photo-abstract-editorial-skill`

- This requested name maps to the published `dist/photo-abstract-editorial-skill.zip` from `kwhi6693-web/photo-abstract-editorial`; it is not the same implementation as step 1.
- Read `.agents/skills/photo-abstract-editorial-skill/SKILL.md` and `references/art-direction.md` completely.
- Follow its verified pipeline exactly: generate only a sparse source-derived motif on a flat chroma key, remove the key with imagegen's installed `remove_chroma_key.py`, and use the packaged deterministic compositor for the photograph, uniform panel, and exact local typography.
- Run `scripts/compose_editorial.py --help` before composing. Keep the composed PNG and its manifest in `.work/`, then run `scripts/validate_editorial.py` against source, staged output, and manifest. Continue only after exit code zero and JSON containing `"ok": true`; also complete visual QA. Stop after two motif attempts.
- Copy only the validated PNG to `03-photo-abstract-editorial-skill.png`.

### 4. `gc-minimal-zine-poster`

- Read `.agents/skills/gc-minimal-zine-poster/SKILL.md` plus `references/style-system.md`, `prompt-compiler.md`, `variation-engine.md`, and `quality-gate.md` completely.
- Use Photo Input Mode with the actual source as an edit target. Default to High preservation for identifiable people, pets, products, characters, and artworks.
- Generate a vertical 3:5 paper poster with 70%–90% negative space, one 8%–25% focal event, sparse typography, print/scan materiality, and one visible saturated accent.
- Inspect source preservation and poster quality. If a central gate fails, tighten the prompt and regenerate once.
- Save only the accepted PNG as `04-gc-minimal-zine-poster.png`.

### 5. `photo-relic-editorial`

- Read `.agents/skills/photo-relic-editorial/SKILL.md` and `references/afterimage-editorial-prompt.md` completely.
- Pass the actual source image to generation. Preserve a truthful photographic region and pair it with one recognizable, source-derived lower memory-print relic.
- Use warm paper, deep ink, few deliberate marks, at most one source-supported warm accent, generous blank space, and tiny or absent title text.
- Reject a redrawn or beautified photo, vague color fields, literal illustration, generic geometry, collage clutter, UI, logo, or watermark. Regenerate once if a major upstream gate fails.
- Save only the accepted PNG as `05-photo-relic-editorial.png`.

## Final gate

Run:

```bash
python3 scripts/verify_outputs.py outputs/<photo-folder>
```

The command must report five valid, non-empty PNGs with the exact names below:

```text
01-photo-abstract-editorial.png
02-pixel-style-poster-skill.png
03-photo-abstract-editorial-skill.png
04-gc-minimal-zine-poster.png
05-photo-relic-editorial.png
```

Return the absolute output folder and five image paths. Briefly report any remaining preservation limitation; never describe a failed gate as successful.
