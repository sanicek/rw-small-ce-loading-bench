#!/usr/bin/env python3
"""Compose the deterministic Small CE Loading Bench about-page preview."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


CANVAS = (1234, 500)
TITLE = "Small CE Loading Bench"
STEEL = (160, 178, 181)
FONT_SIZE = 72
FONT_SHA256 = "586556501565e46ad356a5efcc2f6e81375230323ad5a2a1c4cc8211a6c5ef2e"
TEXTURE_SHA256 = "06280e4a31a5a20644028a2a27405ee241e1a189f5d9d9600ceb398d1cc6b1e9"
MASK_SHA256 = "219035638caae1b08f673f6ed35bfc1f88e78e7570241630e05347f13f07e88f"
CE_BADGE_SHA256 = "9261528d1dca7c1f56d2866691119ff5bb22e1899a4c09cf983d3945036b7b09"
FONT_CANDIDATES = (
    Path("/usr/share/fonts/TTF/DejaVuSansCondensed-Bold.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf"),
)


class PreviewError(ValueError):
    """Describe an input that cannot reproduce the accepted preview design."""


def sha256(path: Path) -> str:
    """Identify one source independently of its local filesystem location."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_source(path: Path, expected: str, label: str) -> None:
    """Reject missing or drifted inputs before they can alter candidate pixels."""

    if not path.is_file() or path.is_symlink():
        raise PreviewError(f"{label} must be a regular file: {path}")
    if sha256(path) != expected:
        raise PreviewError(f"{label} bytes do not match the documented source: {path}")


def default_font() -> Path:
    """Locate the documented font without accepting a lookalike substitution."""

    for path in FONT_CANDIDATES:
        if path.is_file() and sha256(path) == FONT_SHA256:
            return path
    raise PreviewError("the documented DejaVu Sans Condensed Bold font was not found; pass --font")


def recolor(texture: Image.Image, mask: Image.Image, color: tuple[int, int, int]) -> Image.Image:
    """Approximate RimWorld CutoutComplex's primary stuff-color channel."""

    output = texture.convert("RGBA")
    source = output.load()
    channels = mask.convert("RGBA").load()
    for y in range(output.height):
        for x in range(output.width):
            red = channels[x, y][0] / 255
            if red <= 0:
                continue
            original = source[x, y]
            tinted = tuple(round(original[index] * color[index] / 255) for index in range(3))
            source[x, y] = tuple(
                round(original[index] * (1 - red) + tinted[index] * red) for index in range(3)
            ) + (original[3],)
    return output


def compose_preview(
    texture: Image.Image,
    mask: Image.Image,
    badge: Image.Image,
    font_path: Path,
) -> Image.Image:
    """Lay out the exact title card while retaining the texture's pixel-art edges."""

    if texture.size != (128, 128) or mask.size != texture.size:
        raise PreviewError("loading-bench texture and mask must both be 128x128")
    if badge.size != (300, 100):
        raise PreviewError("Combat Extended compatibility badge must be 300x100")
    canvas = Image.new("RGB", CANVAS, "black")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(font_path, FONT_SIZE)
    title_box = draw.textbbox((0, 0), TITLE, font=font)
    title_width = title_box[2] - title_box[0]
    title_x = (CANVAS[0] - title_width) // 2 - title_box[0]
    draw.text((title_x, 28 - title_box[1]), TITLE, fill="white", font=font)

    bench = recolor(texture, mask, STEEL).resize((256, 256), Image.Resampling.NEAREST)
    bench_x = (CANVAS[0] - bench.width) // 2
    canvas.paste(bench, (bench_x, 205), bench)
    badge = badge.convert("RGBA")
    canvas.paste(badge, (32, 368), badge)
    return canvas


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("badge", type=Path, help="canonical Combat Extended compatibility badge")
    parser.add_argument("output", type=Path, help="external source candidate to create")
    parser.add_argument("--font", type=Path, help="documented DejaVu Sans Condensed Bold font")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    texture_path = repo_root / "Textures/Things/Building/SmallCELoadingBench/LoadingBench.png"
    mask_path = texture_path.with_name("LoadingBench_m.png")
    badge_path = args.badge.expanduser().resolve()
    font_path = args.font.expanduser().resolve() if args.font else default_font()
    require_source(texture_path, TEXTURE_SHA256, "loading-bench texture")
    require_source(mask_path, MASK_SHA256, "loading-bench mask")
    require_source(badge_path, CE_BADGE_SHA256, "Combat Extended compatibility badge")
    require_source(font_path, FONT_SHA256, "title font")

    with Image.open(texture_path) as texture, Image.open(mask_path) as mask, Image.open(badge_path) as badge:
        preview = compose_preview(texture, mask, badge, font_path)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    preview.save(args.output, format="PNG", optimize=True)
    print(f"About preview source candidate: {args.output.resolve()}")


if __name__ == "__main__":
    try:
        main()
    except PreviewError as error:
        raise SystemExit(f"Error: {error}") from error
