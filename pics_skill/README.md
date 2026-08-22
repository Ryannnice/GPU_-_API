# Repository-scoped photo skills

This directory contains five project-local photo skills plus one batch
orchestrator. They are installed under `.agents/skills`, so Codex discovers
them only when it is launched from this repository directory (or one of its
subdirectories).

## Run the five-style workflow

Open this directory as the Codex working directory, then invoke:

```text
$photo-five-style-batch /absolute/path/to/photo.jpg
```

Each run creates a new directory under `outputs/<photo-name>/` containing five
final PNG images. Image generation/editing is mandatory; the workflow also
runs deterministic composition and pixel validation where required.

`run_5skills_batch.py` is retained only as an explicitly enabled legacy Pillow
preview. It does not execute the five skills and refuses to run unless
`--legacy-filter-fallback` is supplied.

## Installed skills

- `photo-abstract-editorial`
- `pixel-style-poster-skill`
- `photo-abstract-editorial-skill`
- `gc-minimal-zine-poster-v0-3`
- `photo-relic-editorial`

The two `photo-abstract-editorial` package names share the same upstream design
system. The batch skill uses different supported layout and motif overrides so
their output variants remain visibly distinct; it does not present them as two
unrelated upstream styles.

The upstream Git checkouts remain beside this README for local audit and update
work, but are ignored by the parent repository. The self-contained runtime
copies under `.agents/skills` are the versions committed and pushed.

## Curated result

The verified regeneration for `xch.jpg` is saved in:

```text
outputs/xch/20260822_153128_regenerated/
```
