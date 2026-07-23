#!/usr/bin/env python3
"""Validate Small CE Loading Bench's gameplay and texture contracts."""

from __future__ import annotations

import argparse
import hashlib
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


PATCH_PATH = Path("Patches/SmallCELoadingBench/AmmoBench.xml")
TEXTURE_ROOT = Path("Textures/Things/Building/SmallCELoadingBench")
PUBLISHED_FILE_ID = "3770434354"
EXPECTED_OPERATIONS = (
    ("PatchOperationReplace", 'Defs/ThingDef[defName="AmmoBench"]/size', (("size", "(1,1)"),)),
    (
        "PatchOperationReplace",
        'Defs/ThingDef[defName="AmmoBench"]/graphicData/texPath',
        (("texPath", "Things/Building/SmallCELoadingBench/LoadingBench"),),
    ),
    (
        "PatchOperationReplace",
        'Defs/ThingDef[defName="AmmoBench"]/graphicData/graphicClass',
        (("graphicClass", "Graphic_Single"),),
    ),
    (
        "PatchOperationReplace",
        'Defs/ThingDef[defName="AmmoBench"]/graphicData/drawSize',
        (("drawSize", "(1.5,1.5)"),),
    ),
    (
        "PatchOperationAdd",
        'Defs/ThingDef[defName="AmmoBench"]/graphicData',
        (("drawRotated", "false"), ("allowFlip", "false"), ("drawOffset", "(0,0,-0.1)")),
    ),
    ("PatchOperationAdd", 'Defs/ThingDef[defName="AmmoBench"]', (("rotatable", "true"),)),
)
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
EXPECTED_TEXTURE_HASHES = {
    "LoadingBench.png": "d0c6a2a685ca4f97081e2b12fd3cffefdfe80280ddb65fe195ef172297bbb66d",
    "LoadingBench_m.png": "0fd5cb99b3d04901aa56bb92928454f7b106ededbf6ae1d101d5c3b027de76f3",
}


class ModValidationError(ValueError):
    """Describe one violated gameplay-specific package invariant."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ModValidationError(message)


def validate_patch(package: Path) -> None:
    path = package / PATCH_PATH
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError) as error:
        raise ModValidationError(f"cannot read gameplay patch {path}: {error}") from error

    require(root.tag == "Patch", "gameplay patch root must be <Patch>")
    top_level = root.findall("Operation")
    require(len(top_level) == 1, "gameplay patch requires exactly one top-level operation")
    sequence = top_level[0]
    require(sequence.get("Class") == "PatchOperationSequence", "gameplay patch must be an atomic sequence")
    operations = sequence.findall("./operations/li")
    require(len(operations) == len(EXPECTED_OPERATIONS), "gameplay patch operation set has drifted")

    actual = []
    for operation in operations:
        xpath = (operation.findtext("xpath") or "").strip()
        value = operation.find("value")
        require(value is not None, f"patch operation has no value: {xpath}")
        fields = tuple((child.tag, (child.text or "").strip()) for child in value)
        actual.append((operation.get("Class"), xpath, fields))
    require(tuple(actual) == EXPECTED_OPERATIONS, "gameplay patch no longer implements the fixed 1x1 contract")


def validate_texture(path: Path) -> None:
    try:
        header = path.read_bytes()[:33]
    except OSError as error:
        raise ModValidationError(f"cannot read required texture {path}: {error}") from error
    require(len(header) == 33 and header.startswith(PNG_SIGNATURE), f"invalid PNG header: {path}")
    length, chunk = struct.unpack(">I4s", header[8:16])
    require(length == 13 and chunk == b"IHDR", f"PNG must begin with IHDR: {path}")
    width, height, depth, color_type = struct.unpack(">IIBB", header[16:26])
    require((width, height) == (128, 128), f"texture must be 128x128: {path}")
    require((depth, color_type) == (8, 6), f"texture must be 8-bit RGBA: {path}")


def validate_mod(package: Path) -> None:
    package = package.resolve()
    validate_patch(package)
    texture = package / TEXTURE_ROOT / "LoadingBench.png"
    mask = package / TEXTURE_ROOT / "LoadingBench_m.png"
    validate_texture(texture)
    validate_texture(mask)
    for path in (texture, mask):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        require(digest == EXPECTED_TEXTURE_HASHES[path.name], f"approved runtime artwork bytes changed: {path}")
    require(texture.read_bytes() != mask.read_bytes(), "diffuse texture and recolor mask must differ")
    published_id = package / "About" / "PublishedFileId.txt"
    try:
        actual_id = published_id.read_text(encoding="ascii").strip()
    except OSError as error:
        raise ModValidationError(f"cannot read Workshop publication identity {published_id}: {error}") from error
    require(actual_id == PUBLISHED_FILE_ID, "Workshop publication identity has drifted")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    args = parser.parse_args()
    try:
        validate_mod(args.package)
    except ModValidationError as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    print(f"Validated Small CE Loading Bench gameplay contract: {args.package.resolve()}")


if __name__ == "__main__":
    main()
