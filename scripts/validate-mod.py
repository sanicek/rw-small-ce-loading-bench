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
        (("drawRotated", "false"), ("allowFlip", "false")),
    ),
    ("PatchOperationAdd", 'Defs/ThingDef[defName="AmmoBench"]', (("rotatable", "true"),)),
)
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
EXPECTED_TEXTURE_HASHES = {
    "LoadingBench.png": "fc3aff67a72a181a35b0dffcccce36a8d14632ddeb47a5cb594e5944421750a2",
    "LoadingBench_m.png": "d04af9edf226198dbf6dca48571a1b0055f28766e97ee4ff943ff6021da68785",
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
        require(digest == EXPECTED_TEXTURE_HASHES[path.name], f"approved template bytes changed: {path}")
    require(texture.read_bytes() != mask.read_bytes(), "diffuse texture and recolor mask must differ")


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
