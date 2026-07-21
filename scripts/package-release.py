#!/usr/bin/env python3
"""Build one deterministic, validator-approved GitHub release archive."""

from __future__ import annotations

import hashlib
import fcntl
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from project import ProjectError, load_project
from release_archive import ArchiveError, preflight_release


ARCHIVE_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def fail(message: str) -> None:
    print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(1)


def archive_entry(name: str, mode: int, directory: bool = False) -> zipfile.ZipInfo:
    entry = zipfile.ZipInfo(name + ("/" if directory else ""), ARCHIVE_TIMESTAMP)
    entry.create_system = 3
    entry.external_attr = ((mode & 0xFFFF) << 16) | (0x10 if directory else 0)
    entry.compress_type = zipfile.ZIP_DEFLATED
    return entry


def write_archive(package: Path, destination: Path) -> None:
    """Write stable names, ordering, timestamps, modes, and compressed bytes."""

    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        archive.writestr(archive_entry(package.name, 0o755, directory=True), b"")
        for path in sorted(package.rglob("*"), key=lambda item: item.relative_to(package).as_posix()):
            relative = path.relative_to(package).as_posix()
            archive_name = f"{package.name}/{relative}"
            if path.is_symlink():
                fail(f"release package may not contain symlinks: {path}")
            if path.is_dir():
                archive.writestr(archive_entry(archive_name, 0o755, directory=True), b"")
            elif path.is_file():
                with path.open("rb") as source, archive.open(archive_entry(archive_name, 0o644), "w") as target:
                    shutil.copyfileobj(source, target, length=1024 * 1024)
            else:
                fail(f"release package contains an unsupported entry: {path}")
    with zipfile.ZipFile(destination, "r") as archive:
        corrupt = archive.testzip()
        if corrupt:
            fail(f"release archive failed its CRC check at {corrupt}")


def files_equal(first: Path, second: Path) -> bool:
    if first.stat().st_size != second.stat().st_size:
        return False
    with first.open("rb") as left, second.open("rb") as right:
        while True:
            left_chunk = left.read(1024 * 1024)
            right_chunk = right.read(1024 * 1024)
            if left_chunk != right_chunk:
                return False
            if not left_chunk:
                return True


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=normal"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if status:
        fail("release packaging requires a clean worktree")
    subprocess.run([sys.executable, repo_root / "scripts" / "validate-source.py", repo_root, "--release"], check=True)
    try:
        project = load_project(repo_root / "About" / "About.xml")
    except ProjectError as error:
        fail(str(error))
    artifacts = repo_root / "artifacts"
    artifacts.mkdir(exist_ok=True)
    lock_fd = os.open(artifacts, os.O_RDONLY | os.O_DIRECTORY)
    fcntl.flock(lock_fd, fcntl.LOCK_EX)
    environment = {**os.environ, "ARTIFACT_LOCK_HELD": "1"}
    subprocess.run([repo_root / "scripts" / "build.sh"], check=True, env=environment)

    package = repo_root / "artifacts" / project.package_name
    release_dir = repo_root / "artifacts" / "releases"
    if release_dir.is_symlink() or (release_dir.exists() and not release_dir.is_dir()):
        fail(f"release output must be a real directory: {release_dir}")
    release_dir.mkdir(parents=True, exist_ok=True)
    archive = release_dir / f"{project.package_name}-v{project.version}.zip"
    checksum = archive.with_suffix(".zip.sha256")
    if archive.is_symlink() or checksum.is_symlink():
        fail("release output paths may not be symlinks")
    temporary_fd, temporary_name = tempfile.mkstemp(prefix=f".{archive.name}.", suffix=".tmp", dir=release_dir)
    os.close(temporary_fd)
    temporary = Path(temporary_name)
    try:
        write_archive(package, temporary)
        try:
            preflight_release(temporary, project.package_name)
        except ArchiveError as error:
            fail(str(error))
        if archive.exists():
            if not archive.is_file() or not files_equal(archive, temporary):
                fail(f"existing same-version candidate differs; bump modVersion or remove it after explicit review: {archive}")
        else:
            os.replace(temporary, archive)
    finally:
        temporary.unlink(missing_ok=True)

    digest = sha256_file(archive)
    checksum.write_text(f"{digest}  {archive.name}\n", encoding="ascii")
    print(f"Release archive: {archive}")
    print(f"SHA-256: {digest}")


if __name__ == "__main__":
    main()
