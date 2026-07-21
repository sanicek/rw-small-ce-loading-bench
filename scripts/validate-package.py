#!/usr/bin/env python3
"""Validate generic RimWorld package structure and portable content contracts.

Gameplay-specific invariants belong in a mod-owned extension of this validator.
These checks cover the reusable boundary: metadata, routing, XML, translations,
PNG integrity, assemblies, and accidental package expansion.
"""

from __future__ import annotations

import argparse
import binascii
import re
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath, PureWindowsPath

from project import Project, ProjectError, load_project


CONTENT_DIRECTORIES = {"About", "Biomes", "Common", "Defs", "Languages", "Patches", "Sounds", "Textures"}
CONTENT_FILES = {"LICENSE", "LoadFolders.xml", "THIRD_PARTY_NOTICES.md"}
VERSION_DIRECTORY = re.compile(r"^\d+\.\d+$")
PLACEHOLDER = re.compile(r"\{[^{}]+\}")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class ValidationError(ValueError):
    """Describe one package contract violation."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def parse_xml(path: Path) -> ET.Element:
    try:
        return ET.parse(path).getroot()
    except (OSError, ET.ParseError) as error:
        raise ValidationError(f"invalid XML in {path}: {error}") from error


def validate_tree(package: Path, project: Project) -> None:
    require(package.is_dir(), f"package directory does not exist: {package}")
    require(package.name == project.package_name, f"package directory must be named {project.package_name!r}")
    for path in package.rglob("*"):
        require(not path.is_symlink(), f"package may not contain symlinks: {path}")
        require(not path.name.startswith("."), f"package may not contain hidden entries: {path}")

    for entry in package.iterdir():
        if entry.is_dir():
            allowed = entry.name in CONTENT_DIRECTORIES or entry.name in project.supported_versions
            require(allowed, f"unexpected top-level directory: {entry.name}")
        elif entry.is_file():
            require(entry.name in CONTENT_FILES, f"unexpected top-level file: {entry.name}")
        else:
            raise ValidationError(f"unsupported top-level entry: {entry}")

    require((package / "About" / "About.xml").is_file(), "About/About.xml is required")
    require((package / "LoadFolders.xml").is_file(), "LoadFolders.xml is required")
    for path in package.iterdir():
        if path.is_dir() and VERSION_DIRECTORY.fullmatch(path.name):
            require(path.name in project.supported_versions, f"version directory {path.name} is not declared in About.xml")


def validate_metadata(package: Path, project: Project) -> None:
    root = parse_xml(package / "About" / "About.xml")
    require(root.tag == "ModMetaData", "About/About.xml root must be <ModMetaData>")
    description = root.findtext("description", "").strip()
    require(description, "About/About.xml requires a non-empty <description>")
    url = root.findtext("url", "").strip()
    require(url.startswith("https://"), "About/About.xml <url> must use HTTPS")

    published = package / "About" / "PublishedFileId.txt"
    if published.exists():
        value = published.read_text(encoding="ascii").strip()
        require(bool(re.fullmatch(r"[1-9]\d*", value)), "PublishedFileId.txt must contain one positive numeric Workshop ID")


def validate_load_folders(package: Path, project: Project) -> None:
    root = parse_xml(package / "LoadFolders.xml")
    require(root.tag == "loadFolders", "LoadFolders.xml root must be <loadFolders>")
    expected_tags = {f"v{version}" for version in project.supported_versions}
    child_tags = [child.tag for child in root]
    actual_tags = set(child_tags)
    require(len(child_tags) == len(actual_tags), "LoadFolders.xml may not repeat version elements")
    require(actual_tags == expected_tags, f"LoadFolders.xml versions must be {sorted(expected_tags)}, found {sorted(actual_tags)}")

    mappings: dict[str, set[str]] = {}
    for version in project.supported_versions:
        element = root.find(f"v{version}")
        assert element is not None
        paths = [item.text.strip() for item in element.findall("li") if item.text and item.text.strip()]
        require(paths, f"LoadFolders.xml v{version} requires at least one path")
        normalized: set[str] = set()
        for value in paths:
            posix = PurePosixPath(value)
            windows = PureWindowsPath(value)
            safe = (
                value == "/"
                or (
                    "\\" not in value
                    and not posix.is_absolute()
                    and not windows.is_absolute()
                    and not windows.drive
                    and ".." not in posix.parts
                    and ".." not in windows.parts
                )
            )
            require(safe, f"unsafe load folder path for {version}: {value!r}")
            target = package if value == "/" else package / value
            require(target.is_dir(), f"load folder path does not exist for {version}: {value}")
            require(target.resolve().is_relative_to(package.resolve()), f"load folder escapes package for {version}: {value!r}")
            normalized.add(value)
        mappings[version] = normalized

    for version in project.supported_versions:
        assemblies = package / version / "Assemblies"
        if assemblies.exists():
            require(version in mappings[version], f"v{version} must load {version!r} when versioned assemblies exist")
            dlls = list(assemblies.glob("*.dll"))
            require(dlls, f"{version}/Assemblies must contain at least one DLL")
            unexpected = [path for path in assemblies.iterdir() if not path.is_file() or path.suffix.lower() != ".dll"]
            require(not unexpected, f"unexpected assembly entry: {unexpected[0] if unexpected else ''}")


def keyed_catalog(path: Path) -> dict[str, tuple[str, ...]]:
    root = parse_xml(path)
    require(root.tag == "LanguageData", f"keyed catalog root must be <LanguageData>: {path}")
    entries: dict[str, tuple[str, ...]] = {}
    for child in root:
        require(child.tag not in entries, f"duplicate translation key {child.tag!r} in {path}")
        text = "".join(child.itertext())
        entries[child.tag] = tuple(PLACEHOLDER.findall(text))
    return entries


def validate_languages(package: Path) -> None:
    languages = package / "Languages"
    if not languages.exists():
        return
    english_keyed = languages / "English" / "Keyed"
    require(english_keyed.is_dir(), "Languages requires an English/Keyed source catalog")
    source_paths = sorted(
        path.relative_to(english_keyed)
        for path in english_keyed.rglob("*")
        if path.is_file() and path.suffix.lower() == ".xml"
    )
    require(bool(source_paths), "English/Keyed requires at least one XML catalog")
    source: dict[Path, dict[str, tuple[str, ...]]] = {}
    source_keys: set[str] = set()
    for relative in source_paths:
        catalog = keyed_catalog(english_keyed / relative)
        duplicates = source_keys.intersection(catalog)
        require(not duplicates, f"duplicate English translation key across catalogs: {next(iter(duplicates), '')}")
        source_keys.update(catalog)
        source[relative] = catalog

    for language in sorted(path for path in languages.iterdir() if path.is_dir() and path.name != "English"):
        keyed = language / "Keyed"
        translated_paths = (
            sorted(
                path.relative_to(keyed)
                for path in keyed.rglob("*")
                if path.is_file() and path.suffix.lower() == ".xml"
            )
            if keyed.is_dir()
            else []
        )
        require(translated_paths == source_paths, f"{language.name} Keyed catalogs must match English")
        translated_keys: set[str] = set()
        for relative, expected in source.items():
            actual = keyed_catalog(keyed / relative)
            duplicates = translated_keys.intersection(actual)
            require(not duplicates, f"duplicate {language.name} translation key across catalogs: {next(iter(duplicates), '')}")
            translated_keys.update(actual)
            require(actual.keys() == expected.keys(), f"translation keys differ in {language.name}/Keyed/{relative}")
            for key, placeholders in expected.items():
                require(actual[key] == placeholders, f"placeholders differ for {key} in {language.name}/Keyed/{relative}")


def validate_png(path: Path) -> None:
    data = path.read_bytes()
    require(data.startswith(PNG_SIGNATURE), f"invalid PNG signature: {path}")
    offset = len(PNG_SIGNATURE)
    seen_ihdr = False
    seen_idat = False
    seen_iend = False
    while offset < len(data):
        require(offset + 12 <= len(data), f"truncated PNG chunk in {path}")
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        chunk_type = data[offset + 4 : offset + 8]
        end = offset + 12 + length
        require(end <= len(data), f"truncated PNG data in {path}")
        payload = data[offset + 8 : offset + 8 + length]
        expected_crc = struct.unpack(">I", data[offset + 8 + length : end])[0]
        actual_crc = binascii.crc32(chunk_type + payload) & 0xFFFFFFFF
        require(actual_crc == expected_crc, f"PNG CRC mismatch in {path}")
        if chunk_type == b"IHDR":
            require(not seen_ihdr and length == 13, f"invalid PNG IHDR in {path}")
            width, height = struct.unpack(">II", payload[:8])
            require(width > 0 and height > 0, f"invalid PNG dimensions in {path}")
            seen_ihdr = True
        elif chunk_type == b"IEND":
            require(length == 0, f"invalid PNG IEND in {path}")
            seen_iend = True
            require(end == len(data), f"trailing data after PNG IEND in {path}")
        elif chunk_type == b"IDAT":
            seen_idat = True
        offset = end
    require(seen_ihdr and seen_idat and seen_iend, f"incomplete PNG structure: {path}")


def validate_content(package: Path) -> None:
    for path in package.rglob("*"):
        if path.is_file() and path.suffix.lower() == ".xml":
            parse_xml(path)
        if path.is_file() and path.suffix.lower() == ".png":
            validate_png(path)


def warn_installed_version(rimworld_dir: Path | None, project: Project) -> None:
    if rimworld_dir is None:
        return
    version_file = rimworld_dir / "Version.txt"
    if not version_file.is_file():
        print(f"Warning: cannot inspect installed RimWorld version at {version_file}", file=sys.stderr)
        return
    installed = version_file.read_text(encoding="utf-8", errors="replace")
    if not any(version in installed for version in project.supported_versions):
        print(f"Warning: installed RimWorld version is outside {project.supported_versions}", file=sys.stderr)


def validate(package: Path, rimworld_dir: Path | None = None) -> Project:
    metadata = package / "About" / "About.xml"
    try:
        project = load_project(metadata)
    except ProjectError as error:
        raise ValidationError(str(error)) from error
    validate_tree(package, project)
    validate_metadata(package, project)
    validate_load_folders(package, project)
    validate_languages(package)
    validate_content(package)
    warn_installed_version(rimworld_dir, project)
    return project


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("--rimworld-dir", type=Path)
    args = parser.parse_args()
    try:
        project = validate(args.package.resolve(), args.rimworld_dir)
    except ValidationError as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    print(f"Validated {project.name} {project.version}: {args.package.resolve()}")


if __name__ == "__main__":
    main()
