# Project-local photo workflow

These instructions apply only inside `/renyuanliu/temp/pix-skill`.

When the user supplies one photograph and asks for the five-style treatment—or sends only an image path in the established task context—read `WORKFLOW.md` completely and execute it. The five installed skills live only under `.agents/skills/`.

Hard rules:

- Always use the original input photograph independently for all five variants. Run the variants sequentially in the order specified in `WORKFLOW.md`; never feed one generated variant into the next.
- Before each variant, read that installed skill's full `SKILL.md` and every reference it requires for generation.
- Use the built-in image-generation/editing capability with the actual source image. Do not substitute a Pillow/OpenCV filter, a color overlay, a prompt-only response, or any legacy runner from `../pics_skill`.
- Inspect the source and every generated raster visually. Apply each upstream skill's quality gate and retry limit.
- Put intermediate images, prompts, manifests, and logs under `.work/`. Each final photo folder under `outputs/` must contain exactly the five PNG files named in `WORKFLOW.md` and nothing else.
- Never overwrite an existing completed photo folder. Follow the repeat-run naming rule in `WORKFLOW.md`.
- Do not claim a particular image model name unless the generation tool explicitly reports it.
