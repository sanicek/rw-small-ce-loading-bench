"""Validate bounded, single-root release archives before use."""

from __future__ import annotations

import stat
import zipfile
from pathlib import Path, PurePosixPath


MAX_ENTRIES = 10_000
MAX_MEMBER_SIZE = 256 * 1024 * 1024
MAX_TOTAL_SIZE = 1024 * 1024 * 1024
MAX_COMPRESSION_RATIO = 200


class ArchiveError(ValueError):
    """Describe an archive that is unsafe or outside the package contract."""


def validate_open_archive(archive: zipfile.ZipFile, package_name: str) -> None:
    entries = archive.infolist()
    if not entries or len(entries) > MAX_ENTRIES:
        raise ArchiveError("release archive has an invalid entry count")
    names = [entry.filename for entry in entries]
    if len(names) != len(set(names)):
        raise ArchiveError("release archive contains duplicate names")

    total = 0
    for entry in entries:
        path = PurePosixPath(entry.filename)
        if path.is_absolute() or ".." in path.parts or not path.parts or path.parts[0] != package_name:
            raise ArchiveError(f"unsafe or unexpected release entry: {entry.filename}")
        if "\\" in entry.filename:
            raise ArchiveError(f"release entry must use forward slashes: {entry.filename}")
        normalized_name = path.as_posix() + ("/" if entry.is_dir() else "")
        if normalized_name != entry.filename:
            raise ArchiveError(f"release entry is not canonically named: {entry.filename}")
        mode = entry.external_attr >> 16
        if stat.S_ISLNK(mode):
            raise ArchiveError(f"release archive may not contain symlinks: {entry.filename}")
        if entry.file_size > MAX_MEMBER_SIZE:
            raise ArchiveError(f"release member is too large: {entry.filename}")
        total += entry.file_size
        if total > MAX_TOTAL_SIZE:
            raise ArchiveError("release archive expands beyond the total size limit")
        if entry.compress_size and entry.file_size / entry.compress_size > MAX_COMPRESSION_RATIO:
            raise ArchiveError(f"release member compression ratio is too high: {entry.filename}")
    if f"{package_name}/" not in names:
        raise ArchiveError(f"release archive is missing its {package_name}/ root")


def preflight_release(archive_path: Path, package_name: str) -> None:
    with zipfile.ZipFile(archive_path) as archive:
        validate_open_archive(archive, package_name)


def extract_release(archive_path: Path, destination: Path, package_name: str) -> None:
    with zipfile.ZipFile(archive_path) as archive:
        validate_open_archive(archive, package_name)
        archive.extractall(destination)
