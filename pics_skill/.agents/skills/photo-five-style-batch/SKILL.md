---
name: photo-five-style-batch
description: Use when one supplied photograph or local image path must be processed into five genuinely generated editorial variants using the five repository-local photo skills. Trigger for 五种风格, 五张图, batch photo styles, or requests to run/regenerate the pics_skill workflow. Never use the legacy Pillow filter fallback as the final workflow.
---

# Five Photo Styles Batch

Turn one source photograph into five visually distinct images by following the five repository-local skills. Use the built-in image-generation/editing tool wherever a child skill requires generation. A Pillow-only or filter-only approximation is not a valid result.

## Inputs and outputs

- Require one readable source image. Inspect it with `view_image` before prompting.
- Create a new directory at `outputs/<source-stem>/<UTC timestamp>_generated/`; never overwrite an earlier run.
- Deliver exactly these five final PNG files:
  - `photo-abstract-editorial.png`
  - `pixel-style-poster-skill.png`
  - `photo-abstract-editorial-skill.png`
  - `gc-minimal-zine-poster-v0-3.png`
  - `photo-relic-editorial.png`
- Validator manifests may sit beside the two abstract images. Keep generation intermediates outside the final directory.

## Required workflow

1. Read the complete `SKILL.md` for all five local skills before generation. Read every reference each selected skill marks as required.
2. Record three to six visible source facts and identity-preservation invariants. For people, preserve count, identity, facial structure, pose, left/right relationship, clothing, hands, and important held objects unless the user authorizes changes.
3. Run `photo-abstract-editorial` exactly as specified: use image generation only for a text-free motif on a flat chroma key, remove the key with imagegen's installed `remove_chroma_key.py`, assemble with the repository compositor, validate with `validate_editorial.py`, then inspect visually.
4. Run `pixel-style-poster-skill` in Standard Mode with the actual source image supplied to image generation. Enforce a 3:4 editorial bitmap print, fine dot matrix, a restrained ink system, and the skill's anti-game constraints.
5. Run `photo-abstract-editorial-skill` through the same verified motif/compositor contract. This local package is a second copy of the same upstream design system, so choose a visibly different legal override from step 3, such as bottom-center rather than lower-left, organic masses rather than stacked bands, a different panel height, and a different exact title. Do not claim it is an unrelated upstream style.
6. Run `gc-minimal-zine-poster-v0-3` in Photo Input Mode with the supplied image as a high-preservation edit target. Use a 3:5 paper poster, 70%-90% open paper, one small visual event, and one clear saturated accent.
7. Run `photo-relic-editorial` with the actual source image. Preserve a truthful real-photo region and generate a recognizable lower memory-print relic. If image generation redraws the photographic region, retain the generated relic but deterministically replace the photo region with the original source pixels before delivery.
8. Inspect all five final rasters. They must differ in composition grammar, not only color. Allow one targeted regeneration per failed skill. Reject extra people, extra hands or held objects, distorted identity, unwanted text, watermarks, UI, or a result that is merely a filter.
9. Re-run both abstract validators. For every deterministically preserved photo region, compare decoded frame hashes or pixels with the source. Confirm the final directory contains five PNG images and report the saved path.

## Legacy guard

`run_5skills_batch.py` is only an explicitly enabled local preview fallback. It does not invoke Codex image generation and must never be presented as execution of these five skills.
