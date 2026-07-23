#!/usr/bin/env python3
"""Extract one generated fixture and place it on the canonical blank bench."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageFilter


def _neutral_background_alpha(fixture: Image.Image) -> Image.Image:
    """Separate authored fixture pixels from a light neutral backing layer."""

    fixture = fixture.convert("RGB")
    alpha = Image.new("L", fixture.size, 0)
    alpha_pixels = alpha.load()
    pixels = fixture.load()
    assert alpha_pixels is not None and pixels is not None
    for y in range(fixture.height):
        for x in range(fixture.width):
            red, green, blue = pixels[x, y]
            luminance = (2126 * red + 7152 * green + 722 * blue) / 10000
            chroma = max(red, green, blue) - min(red, green, blue)
            dark_alpha = max(0.0, min(1.0, (205 - luminance) / 22))
            color_alpha = max(0.0, min(1.0, (chroma - 10) / 25))
            alpha_pixels[x, y] = round(255 * max(dark_alpha, color_alpha))

    return alpha


def _cutout_fixture(source: Image.Image, crop: tuple[int, int, int, int]) -> Image.Image:
    """Remove the selected concept panel's light neutral work surface."""

    fixture = source.convert("RGB").crop(crop)
    alpha = _neutral_background_alpha(fixture)

    bounds = alpha.point(lambda value: 255 if value > 8 else 0).getbbox()
    if bounds is None:
        raise ValueError("selected crop contains no fixture against a light neutral background")
    fixture = fixture.convert("RGBA")
    fixture.putalpha(alpha)
    return fixture.crop(bounds)


def _remove_neutral_matte(fixture: Image.Image) -> Image.Image:
    """Recover anti-aliased fixture edges without retaining their pale matte."""

    result = fixture.convert("RGBA")
    pixels = result.load()
    assert pixels is not None
    coverage: dict[tuple[int, int], float] = {}
    for y in range(result.height):
        for x in range(result.width):
            red, green, blue, _ = pixels[x, y]
            luminance = (2126 * red + 7152 * green + 722 * blue) / 10000
            chroma = max(red, green, blue) - min(red, green, blue)
            dark_alpha = max(0.0, min(1.0, (185 - luminance) / 15))
            color_alpha = max(0.0, min(1.0, (chroma - 10) / 25))
            alpha = max(dark_alpha, color_alpha)
            if alpha > 8 / 255:
                coverage[x, y] = alpha

    # Generated backing can contain faint disconnected marks. The press and
    # lever form one assembly, so retaining its largest component removes those
    # marks without eroding the connected anti-aliased silhouette.
    remaining = set(coverage)
    components: list[set[tuple[int, int]]] = []
    while remaining:
        pending = [remaining.pop()]
        component = set(pending)
        while pending:
            x, y = pending.pop()
            for neighbor_y in range(y - 1, y + 2):
                for neighbor_x in range(x - 1, x + 2):
                    neighbor = (neighbor_x, neighbor_y)
                    if neighbor in remaining:
                        remaining.remove(neighbor)
                        component.add(neighbor)
                        pending.append(neighbor)
        components.append(component)
    retained = max(components, key=len) if components else set()

    for y in range(result.height):
        for x in range(result.width):
            red, green, blue, _ = pixels[x, y]
            alpha = coverage.get((x, y), 0.0) if (x, y) in retained else 0.0
            if not alpha:
                pixels[x, y] = (red, green, blue, 0)
                continue
            luminance = (2126 * red + 7152 * green + 722 * blue) / 10000
            chroma = max(red, green, blue) - min(red, green, blue)
            dark_alpha = max(0.0, min(1.0, (185 - luminance) / 15))
            color_alpha = max(0.0, min(1.0, (chroma - 10) / 25))
            if alpha < 1 and dark_alpha >= color_alpha:
                # The source edge was composited over an approximately 225-value
                # neutral panel. Unmatte it before RimWorld blends it over the base.
                channels = tuple(
                    max(0, min(255, round((channel - 225 * (1 - alpha)) / alpha)))
                    for channel in (red, green, blue)
                )
            else:
                channels = (red, green, blue)
            pixels[x, y] = channels + (round(255 * alpha),)
    return result


def clean_positioned_fixture(
    source: Image.Image,
    base: Image.Image,
    base_mask: Image.Image,
    *,
    crop: tuple[int, int, int, int],
    fixture_mask_red: int = 112,
) -> tuple[Image.Image, Image.Image]:
    """Remove a pasted neutral rectangle while retaining authored placement."""

    if source.size != base.size or base.size != base_mask.size:
        raise ValueError("positioned source, base texture, and mask dimensions differ")
    fixture = _remove_neutral_matte(source.crop(crop))
    position = crop[:2]
    texture = base.convert("RGBA").copy()
    texture.alpha_composite(fixture, position)

    mask = base_mask.convert("RGBA").copy()
    mask_pixels = mask.load()
    fixture_alpha = fixture.getchannel("A").load()
    assert mask_pixels is not None and fixture_alpha is not None
    for y in range(fixture.height):
        for x in range(fixture.width):
            coverage = fixture_alpha[x, y]
            if not coverage:
                continue
            target_x, target_y = position[0] + x, position[1] + y
            red, green, blue, alpha = mask_pixels[target_x, target_y]
            remaining = 255 - coverage
            mask_pixels[target_x, target_y] = (
                round((red * remaining + fixture_mask_red * coverage) / 255),
                round(green * remaining / 255),
                round(blue * remaining / 255),
                alpha,
            )
    mask.putalpha(texture.getchannel("A"))
    return texture, mask


def _mute_fixture(fixture: Image.Image, gamma: float, saturation: float, quantization: int) -> Image.Image:
    """Compress icon-like contrast and color into broader vanilla-style forms."""

    result = fixture.copy()
    pixels = result.load()
    assert pixels is not None
    lookup = tuple(round(255 * (value / 255) ** gamma) for value in range(256))
    for y in range(result.height):
        for x in range(result.width):
            red, green, blue, alpha = pixels[x, y]
            if not alpha:
                continue
            red, green, blue = lookup[red], lookup[green], lookup[blue]
            gray = round(0.2126 * red + 0.7152 * green + 0.0722 * blue)
            channels = tuple(round(gray + (channel - gray) * saturation) for channel in (red, green, blue))
            pixels[x, y] = tuple(min(255, round(channel / quantization) * quantization) for channel in channels) + (alpha,)
    return result


def _soften_fixture(
    fixture: Image.Image,
    size: tuple[int, int],
    detail_scale: float,
    blur_radius: float,
    noise_amplitude: int,
) -> Image.Image:
    """Remove icon-scale detail, then add restrained painted luminance variation."""

    if not 0 < detail_scale <= 1:
        raise ValueError("detail scale must be greater than zero and at most one")
    low_size = (max(1, round(size[0] * detail_scale)), max(1, round(size[1] * detail_scale)))
    fixture = fixture.convert("RGBa").resize(low_size, Image.Resampling.LANCZOS)
    fixture = fixture.resize(size, Image.Resampling.BICUBIC)
    if blur_radius:
        fixture = fixture.filter(ImageFilter.GaussianBlur(blur_radius))
    fixture = fixture.convert("RGBA")

    if noise_amplitude:
        grid_size = (max(2, size[0] // 7), max(2, size[1] // 7))
        noise = Image.new("L", grid_size)
        noise.putdata([
            128 + ((x * 37 + y * 61 + x * y * 11 + 17) % (noise_amplitude * 2 + 1)) - noise_amplitude
            for y in range(grid_size[1])
            for x in range(grid_size[0])
        ])
        noise = noise.resize(size, Image.Resampling.BILINEAR)
        pixels = fixture.load()
        noise_pixels = noise.load()
        assert pixels is not None and noise_pixels is not None
        for y in range(fixture.height):
            for x in range(fixture.width):
                red, green, blue, alpha = pixels[x, y]
                if alpha:
                    delta = noise_pixels[x, y] - 128
                    pixels[x, y] = tuple(max(0, min(255, channel + delta)) for channel in (red, green, blue)) + (alpha,)
    return fixture


def compose_prototype(
    source: Image.Image,
    base: Image.Image,
    base_mask: Image.Image,
    *,
    crop: tuple[int, int, int, int],
    maximum: tuple[int, int],
    center_x: int,
    bottom: int,
    fixture_mask_red: int = 112,
    gamma: float = 0.65,
    saturation: float = 0.65,
    quantization: int = 8,
    detail_scale: float = 0.5,
    blur_radius: float = 0.55,
    noise_amplitude: int = 5,
) -> tuple[Image.Image, Image.Image]:
    """Composite a muted fixture while retaining stronger stuff color on the base."""

    if base.size != base_mask.size:
        raise ValueError("base texture and mask dimensions differ")
    fixture = _mute_fixture(_cutout_fixture(source, crop), gamma, saturation, quantization)
    scale = min(maximum[0] / fixture.width, maximum[1] / fixture.height)
    size = (max(1, round(fixture.width * scale)), max(1, round(fixture.height * scale)))
    fixture = _soften_fixture(fixture, size, detail_scale, blur_radius, noise_amplitude)
    position = (center_x - fixture.width // 2, bottom - fixture.height)

    texture = base.convert("RGBA").copy()
    texture.alpha_composite(fixture, position)

    # Vanilla fixtures use partial red so authored colors also inherit some stuff tint.
    mask = base_mask.convert("RGBA").copy()
    mask_pixels = mask.load()
    fixture_alpha = fixture.getchannel("A").load()
    assert mask_pixels is not None and fixture_alpha is not None
    for y in range(fixture.height):
        target_y = position[1] + y
        if not 0 <= target_y < mask.height:
            continue
        for x in range(fixture.width):
            target_x = position[0] + x
            if not 0 <= target_x < mask.width:
                continue
            coverage = fixture_alpha[x, y]
            if coverage:
                red, green, blue, alpha = mask_pixels[target_x, target_y]
                remaining = 255 - coverage
                mask_pixels[target_x, target_y] = (
                    round((red * remaining + fixture_mask_red * coverage) / 255),
                    round(green * remaining / 255),
                    round(blue * remaining / 255),
                    alpha,
                )
    mask.putalpha(texture.getchannel("A"))
    return texture, mask


def _quadruple(value: str) -> tuple[int, int, int, int]:
    parts = tuple(int(part) for part in value.split(","))
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("expected left,top,right,bottom")
    return parts


def _pair(value: str) -> tuple[int, int]:
    parts = tuple(int(part) for part in value.split(","))
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("expected width,height")
    return parts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("base_texture", type=Path)
    parser.add_argument("base_mask", type=Path)
    parser.add_argument("output_texture", type=Path)
    parser.add_argument("output_mask", type=Path)
    parser.add_argument("--crop", type=_quadruple, required=True)
    parser.add_argument("--maximum", type=_pair, default=(64, 56))
    parser.add_argument("--center-x", type=int, default=64)
    parser.add_argument("--bottom", type=int, default=90)
    parser.add_argument("--fixture-mask-red", type=int, default=112)
    parser.add_argument("--gamma", type=float, default=0.65)
    parser.add_argument("--saturation", type=float, default=0.65)
    parser.add_argument("--quantization", type=int, default=8)
    parser.add_argument("--detail-scale", type=float, default=0.5)
    parser.add_argument("--blur-radius", type=float, default=0.55)
    parser.add_argument("--noise-amplitude", type=int, default=5)
    parser.add_argument(
        "--positioned-source",
        action="store_true",
        help="clean a 128x128 composited source without rescaling or repositioning its fixture",
    )
    args = parser.parse_args()

    with Image.open(args.source) as source, Image.open(args.base_texture) as base, Image.open(args.base_mask) as mask:
        if args.positioned_source:
            texture, composed_mask = clean_positioned_fixture(
                source,
                base,
                mask,
                crop=args.crop,
                fixture_mask_red=args.fixture_mask_red,
            )
        else:
            texture, composed_mask = compose_prototype(
                source,
                base,
                mask,
                crop=args.crop,
                maximum=args.maximum,
                center_x=args.center_x,
                bottom=args.bottom,
                fixture_mask_red=args.fixture_mask_red,
                gamma=args.gamma,
                saturation=args.saturation,
                quantization=args.quantization,
                detail_scale=args.detail_scale,
                blur_radius=args.blur_radius,
                noise_amplitude=args.noise_amplitude,
            )
    texture.save(args.output_texture, format="PNG", compress_level=9)
    composed_mask.save(args.output_mask, format="PNG", compress_level=9)
    print(f"Composed prototype texture: {args.output_texture}")
    print(f"Composed prototype mask: {args.output_mask}")


if __name__ == "__main__":
    main()
