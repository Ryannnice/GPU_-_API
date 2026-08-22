#!/usr/bin/env python3
"""Require exactly the five named, structurally valid PNG outputs."""

from __future__ import annotations

import struct
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:  # The PNG header fallback keeps the verifier dependency-free.
    Image = None


EXPECTED = (
    "01-photo-abstract-editorial.png",
    "02-pixel-style-poster-skill.png",
    "03-photo-abstract-editorial-skill.png",
    "04-gc-minimal-zine-poster.png",
    "05-photo-relic-editorial.png",
)
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def png_dimensions(path: Path) -> tuple[int, int]:
    if Image is not None:
        with Image.open(path) as raster:
            if raster.format != "PNG":
                raise ValueError(f"format is {raster.format}, not PNG")
            dimensions = raster.size
            raster.verify()
        return dimensions

    with path.open("rb") as handle:
        header = handle.read(24)
    if len(header) != 24 or header[:8] != PNG_SIGNATURE or header[12:16] != b"IHDR":
        raise ValueError("not a PNG with a valid IHDR header")
    width, height = struct.unpack(">II", header[16:24])
    if width < 1 or height < 1:
        raise ValueError(f"invalid dimensions {width}x{height}")
    return width, height


def main() -> int:
    if len(sys.argv) != 2:
        print(f"Usage: {Path(sys.argv[0]).name} OUTPUT_DIRECTORY", file=sys.stderr)
        return 2

    output_dir = Path(sys.argv[1]).expanduser().resolve()
    if not output_dir.is_dir():
        print(f"Not a directory: {output_dir}", file=sys.stderr)
        return 1

    actual = tuple(sorted(path.name for path in output_dir.iterdir()))
    expected = tuple(sorted(EXPECTED))
    if actual != expected:
        print("Output directory must contain exactly the five required PNG files.", file=sys.stderr)
        print(f"Expected: {list(expected)}", file=sys.stderr)
        print(f"Actual:   {list(actual)}", file=sys.stderr)
        return 1

    for name in EXPECTED:
        path = output_dir / name
        if not path.is_file() or path.stat().st_size == 0:
            print(f"Missing or empty regular file: {path}", file=sys.stderr)
            return 1
        try:
            width, height = png_dimensions(path)
        except (ValueError, OSError, SyntaxError) as exc:
            print(f"Invalid output {path}: {exc}", file=sys.stderr)
            return 1
        print(f"OK  {name}  {width}x{height}  {path.stat().st_size} bytes")

    print(f"\nVerified five outputs in {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
