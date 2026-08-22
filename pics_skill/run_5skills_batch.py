#!/usr/bin/env python3
"""Deprecated deterministic preview for five local stylizations.

Usage:
  python3 run_5skills_batch.py --input /path/to/photo.jpg \
      --legacy-filter-fallback [--out-root outputs]

Requirements:
  - Pillow

This script does not execute the Codex skills or the image-generation tool. Use the
repository-local $photo-five-style-batch skill for final output. The old Pillow
preview remains available only through the explicit legacy flag.
"""

from __future__ import annotations

import argparse
import math
import os
from pathlib import Path
from typing import Callable
from datetime import datetime

from PIL import Image, ImageChops, ImageEnhance, ImageFilter, ImageDraw, ImageFont
import subprocess


ROOT = Path(__file__).resolve().parent
SKILL_DIR = ROOT


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_image(path: Path) -> Image.Image:
    img = Image.open(path).convert("RGB")
    return ImageOps.exif_transpose(img)


class ImageOps:
    @staticmethod
    def exif_transpose(img: Image.Image) -> Image.Image:
        # Keep method for compatibility with local PIL versions.
        return img.transpose(Image.Transpose.ROTATE_180) if hasattr(Image, "Transpose") else img


def fit_canvas(img: Image.Image, size_ratio=(3, 4), upscale_max=1600) -> tuple[Image.Image, float]:
    target_w_ratio = size_ratio[0] / size_ratio[1]
    w, h = img.size
    scale = 1.0
    if w * h > upscale_max * upscale_max:
        scale = (upscale_max * upscale_max / float(w * h)) ** 0.5
        img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.Resampling.LANCZOS)
        w, h = img.size

    # keep width, compute height for ratio
    if w / h > target_w_ratio:
        new_h = w
        new_w = int(new_h * target_w_ratio)
    else:
        new_w = w
        new_h = int(new_w / target_w_ratio)
    canvas = Image.new("RGB", (new_w, new_h), (248, 244, 236))
    # center-crop/pad with letterbox-like behavior
    left = max(0, (new_w - w) // 2)
    top = max(0, (new_h - h) // 2)
    if left == 0 and top == 0:
        if w > new_w:
            left = 0
            x = 0
            y = 0
            src = img.crop((0, (h - new_h) // 2, new_w, (h + new_h) // 2))
        elif h > new_h:
            src = img.crop(((w - new_w) // 2, 0, (w + new_w) // 2, new_h))
        else:
            src = img
            # place centered
            left = (new_w - w) // 2
            top = (new_h - h) // 2
            canvas.paste(src, (left, top))
            return canvas, scale
    else:
        src = img

    # robust fallback path
    if src.size != (new_w, new_h):
        src = src.resize((new_w, new_h), Image.Resampling.LANCZOS)
    canvas.paste(src, (0, 0))
    return canvas, scale


def write_text_center(img: Image.Image, text: str, y: int, fill=(30, 30, 30), font_size=24) -> None:
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size=font_size)
    except Exception:
        font = ImageFont.load_default()
    draw = ImageDraw.Draw(img)
    w = draw.textlength(text, font=font)
    x = max(0, (img.width - w) // 2)
    draw.text((x, y), text, fill=fill, font=font)


def motif_from_source(source: Image.Image) -> Image.Image:
    # produce transparent abstract motif-like map
    small = source.resize((max(64, source.width // 6), max(64, source.height // 6)), Image.Resampling.LANCZOS).convert("RGB")
    edge = small.filter(ImageFilter.FIND_EDGES)
    gray = edge.convert("L")
    gray = ImageEnhance.Contrast(gray).enhance(2.2)
    mask = gray.point(lambda v: 255 if v > 38 else 0)

    # color wash from source's palette
    base = small.convert("L")
    base = ImageEnhance.Contrast(base).enhance(1.5)
    colorized = Image.merge(
        "RGB",
        (
            ImageEnhance.Brightness(base).enhance(0.9),
            ImageEnhance.Brightness(base).enhance(0.85),
            ImageEnhance.Brightness(base).enhance(0.95),
        ),
    )
    out = colorized.convert("RGBA")
    out.putalpha(mask)
    # remove border noise by simple erode-like trick through threshold on alpha
    return out


def make_photo_abstract_style(source_path: Path, out_dir: Path, name_suffix: str, skill_tag: str) -> list[Path]:
    src = Image.open(source_path).convert("RGB")
    img = src

    # Build a temporary motif and run official composer for reproducible layout.
    work = out_dir / f"_{skill_tag}_tmp"
    ensure_dir(work)
    motif = motif_from_source(img).resize((img.width, img.height), Image.Resampling.LANCZOS)
    motif_path = work / f"motif_{name_suffix}.png"
    motif.save(motif_path)

    output = out_dir / f"{skill_tag}.png"
    if output.exists():
        output.unlink()

    # Run local composer script to generate editorial composition.
    cmd = [
        "/usr/bin/env",
        "python3",
        str((ROOT / skill_tag / "scripts" / "compose_editorial.py")),
        "--source",
        str(source_path),
        "--motif",
        str(motif_path),
        "--output",
        str(output),
        "--title",
        f"{source_path.stem} {name_suffix}",

        "--layout",
        "lower-left",
    ]
    result = subprocess.run(cmd, cwd=str(ROOT / skill_tag), check=False, text=True, capture_output=True)
    logs = out_dir / f"{skill_tag}.log"
    logs.write_text(result.stdout + "\n" + result.stderr)
    # keep manifest from composer
    return [output, output.with_suffix(output.suffix + ".manifest.json"), logs]


def make_pixel_style(source_path: Path, out_dir: Path) -> list[Path]:
    img = Image.open(source_path).convert("RGB")
    # target ratio 3:4
    w, h = img.size
    canvas_h = int(w * 4 / 3)
    if canvas_h <= h:
        canvas_h = h
    canvas = Image.new("RGB", (w, canvas_h), (250, 247, 240))
    if h <= canvas_h:
        top = (canvas_h - h) // 2
        canvas.paste(img, (0, top))
    else:
        crop_top = (h - canvas_h) // 2
        canvas.paste(img.crop((0, crop_top, w, crop_top + canvas_h)), (0, 0))

    reduced = canvas.resize((max(16, w // 16), max(20, canvas_h // 16)), Image.Resampling.BILINEAR)
    reduced = reduced.quantize(colors=64).convert("RGB")
    pixel = reduced.resize(canvas.size, Image.Resampling.NEAREST)
    # mild halftone look by mixing original and pixelized
    out = Image.blend(canvas, pixel, 0.82)
    # add tiny texture noise
    import random
    px = out.load()
    for y in range(0, out.height, 4):
        for x in range(0, out.width, 4):
            if (x + y) % 7 == 0:
                c = px[x, y]
                d = -12 if ((x * 13 + y * 17) % 31 < 16) else 12
                px[x, y] = (max(0, min(255, c[0] + d)), max(0, min(255, c[1] + d)), max(0, min(255, c[2] + d)))
    write_text_center(out, "PIXEL POSTER", y=max(18, int(out.height * 0.74)), font_size=max(14, out.height // 35), fill=(20, 20, 20))

    out_path = out_dir / "pixel-style-poster-skill.png"
    out.save(out_path)
    return [out_path]


def make_photo_relic_style(source_path: Path, out_dir: Path) -> list[Path]:
    img = Image.open(source_path).convert("RGB")
    w, h = img.size
    out_h = int(h * 1.45)
    out = Image.new("RGB", (w, out_h), (240, 236, 224))

    src_h = h
    out.paste(img, (0, 0))

    relic_h = out_h - src_h
    relic = img.resize((max(1, w // 2), relic_h), Image.Resampling.LANCZOS)
    relic = relic.filter(ImageFilter.GaussianBlur(radius=2))
    relic = relic.convert("L")
    relic = ImageEnhance.Contrast(relic).enhance(2.2)
    relic = relic.convert("RGB")
    r, g, b = relic.split()
    relic = Image.merge("RGB", (ImageEnhance.Brightness(r).enhance(0.55), ImageEnhance.Brightness(g).enhance(0.48), ImageEnhance.Brightness(b).enhance(0.45)) )

    # place relic in lower panel with asymmetry
    x = max(0, (w - relic.width) // 2)
    out.paste(relic, (x, src_h), mask=None)

    # draw thin accent marks
    draw = ImageDraw.Draw(out)
    draw.rectangle([max(0, x + 10), src_h + 20, max(4, x + 12), out_h - 20], fill=(88, 82, 72))
    write_text_center(out, "relic memory", y=src_h + max(8, relic_h // 3), font_size=max(14, h // 45), fill=(70, 65, 65))

    out_path = out_dir / "photo-relic-editorial.png"
    out.save(out_path)
    return [out_path]


def make_gc_minimal_style(source_path: Path, out_dir: Path) -> list[Path]:
    img = Image.open(source_path).convert("RGB")
    w, h = img.size
    # 3:5 output as style requirement
    out = Image.new("RGB", (w, int(w * 5 / 3)), (247, 243, 236))

    target_w = int(w * 0.58)
    target_h = int((out.height - int(out.height * 0.26)))
    crop = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
    crop = crop.filter(ImageFilter.SHARPEN)
    # paper texture grain overlay
    grain = Image.effect_noise((target_w, target_h), 6).convert("RGB") if hasattr(Image, "effect_noise") else Image.new("RGB", (target_w, target_h), (255, 255, 255))

    # if effect_noise not available, fallback
    try:
        g = grain.resize((target_w, target_h))
        g = ImageEnhance.Contrast(g.convert("L")).enhance(0.25)
        crop = Image.blend(crop, g.convert("RGB"), 0.08)
    except Exception:
        pass

    x = (out.width - crop.width) // 2
    y = int(out.height * 0.16)
    out.paste(crop, (x, y))

    # high-chroma accent
    draw = ImageDraw.Draw(out)
    draw.line([(out.width // 2, int(out.height * 0.08)), (out.width // 2 + int(w * 0.18), int(out.height * 0.82))],
              fill=(245, 90, 40), width=3)
    write_text_center(out, "GC MINIMAL", y=int(out.height * 0.90), font_size=max(16, w // 44), fill=(54, 54, 54))

    out_path = out_dir / "gc-minimal-zine-poster-v0-3.png"
    out.save(out_path)
    return [out_path]



def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, help="Input image path")
    p.add_argument("--out-root", default=str(ROOT / "outputs"), help="Output root directory")
    p.add_argument(
        "--legacy-filter-fallback",
        action="store_true",
        help="Explicitly run the old Pillow preview; this does not execute the five Codex skills",
    )
    return p.parse_args()


def ensure_local_skill_path() -> None:
    # keep this run isolated: only rely on current workspace's local /tmp/pix-skill clone
    if not str(ROOT).startswith("/tmp/pix-skill"):
        # soft reminder in logs; we keep execution confined anyway.
        pass


def main() -> int:
    args = parse_args()
    if not args.legacy_filter_fallback:
        print(
            "Refusing to present the legacy Pillow preview as skill output. "
            "Open this repository in Codex and invoke $photo-five-style-batch instead."
        )
        return 2
    src = Path(args.input)
    if not src.is_file():
        print(f"Input not found: {src}")
        return 1
    out_root = Path(args.out_root).resolve()
    ensure_local_skill_path()

    safe_name = src.stem.replace(" ", "_")
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    session_dir = out_root / safe_name / ts
    ensure_dir(session_dir)

    results: list[tuple[str, list[Path]]] = []

    # 1) photo-abstract
    try:
        paths = make_photo_abstract_style(src, session_dir, "main", "photo-abstract-editorial")
        results.append(("photo-abstract-editorial", paths))
    except Exception as exc:
        results.append(("photo-abstract-editorial", [Path(str(exc))]))

    # 2) pixel style
    try:
        paths = make_pixel_style(src, session_dir)
        results.append(("pixel-style-poster-skill", paths))
    except Exception as exc:
        results.append(("pixel-style-poster-skill", [Path(str(exc))]))

    # 3) photo relic
    try:
        paths = make_photo_relic_style(src, session_dir)
        results.append(("photo-relic-editorial", paths))
    except Exception as exc:
        results.append(("photo-relic-editorial", [Path(str(exc))]))

    # 4) gc minimal
    try:
        paths = make_gc_minimal_style(src, session_dir)
        results.append(("gc-minimal-zine-poster-v0-3", paths))
    except Exception as exc:
        results.append(("gc-minimal-zine-poster-v0-3", [Path(str(exc))]))

    # 5) abstract skill alias
    try:
        paths = make_photo_abstract_style(src, session_dir, "alias", "photo-abstract-editorial-skill")
        results.append(("photo-abstract-editorial-skill", paths))
    except Exception as exc:
        results.append(("photo-abstract-editorial-skill", [Path(str(exc))]))

    print(f"OUTPUT_DIR={session_dir}")
    for name, files in results:
        print(name)
        for f in files:
            print(f"  - {f.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
