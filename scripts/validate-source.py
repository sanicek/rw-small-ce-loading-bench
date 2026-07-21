#!/usr/bin/env python3
"""Validate repository inputs before copy or destructive artifact operations."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tomllib
from pathlib import Path

from project import ProjectError, load_project


DIRECTORIES = ("About", "Biomes", "Common", "Defs", "Languages", "Patches", "Sounds", "Textures")
FILES = ("LoadFolders.xml", "LICENSE", "THIRD_PARTY_NOTICES.md")
TEMPLATE_SENTINELS = ("Example Mod", "ExampleMod", "rw-mod-template")


class SourceError(ValueError):
    """Describe source state that cannot produce a trustworthy package."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SourceError(message)


def ignored(repo_root: Path, path: Path) -> bool:
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", "--", str(path.relative_to(repo_root))],
        cwd=repo_root,
        check=False,
    )
    if result.returncode not in (0, 1):
        raise SourceError(f"git check-ignore failed for {path}")
    return result.returncode == 0


def validate_source(repo_root: Path, release: bool = False) -> None:
    repo_root = repo_root.resolve()
    try:
        project = load_project(repo_root / "About" / "About.xml")
    except ProjectError as error:
        raise SourceError(str(error)) from error

    artifacts = repo_root / "artifacts"
    require(not artifacts.is_symlink(), "artifacts must not be a symlink")
    if artifacts.exists():
        require(artifacts.is_dir(), "artifacts must be a directory")
        require(artifacts.resolve() == artifacts, "artifacts must resolve inside the repository")

    require(not (repo_root / "Assemblies").exists(), "root Assemblies is unsupported; use versioned assemblies through Source/")
    inputs = [repo_root / name for name in DIRECTORIES + FILES if (repo_root / name).exists()]
    inputs.extend(repo_root / version for version in project.supported_versions if (repo_root / version).exists())
    for source in inputs:
        candidates = [source, *source.rglob("*")] if source.is_dir() and not source.is_symlink() else [source]
        for path in candidates:
            require(not path.is_symlink(), f"package source may not contain symlinks: {path}")
            require(path.resolve().is_relative_to(repo_root), f"package source escapes repository: {path}")
            require(not ignored(repo_root, path), f"ignored file or directory would enter package: {path}")

    source_root = repo_root / "Source"
    if source_root.exists() or source_root.is_symlink():
        require(not source_root.is_symlink() and source_root.is_dir(), "Source must be a real directory")
        for path in [source_root, *source_root.rglob("*")]:
            require(not path.is_symlink(), f"C# source may not contain symlinks: {path}")
            require(path.resolve().is_relative_to(repo_root), f"C# source escapes repository: {path}")
            relative_parts = path.relative_to(source_root).parts
            generated = any(part in {"bin", "obj"} for part in relative_parts)
            if not generated:
                require(not ignored(repo_root, path), f"ignored C# build input is not reproducible: {path}")

    manifest = repo_root / "artwork" / "manifest.toml"
    if manifest.is_file():
        require(not manifest.is_symlink(), "artwork manifest may not be a symlink")
        try:
            artwork_project = tomllib.loads(manifest.read_text(encoding="utf-8"))["project"]
        except (OSError, tomllib.TOMLDecodeError, KeyError, TypeError) as error:
            raise SourceError(f"invalid artwork manifest identity: {error}") from error
        require(artwork_project.get("package_id") == project.package_id, "artwork package_id must match About/About.xml")
        require(artwork_project.get("name") == project.name, "artwork project name must match About/About.xml")

    if release:
        metadata_text = (repo_root / "About" / "About.xml").read_text(encoding="utf-8")
        require(not any(value in metadata_text for value in TEMPLATE_SENTINELS), "release metadata still contains template placeholders")
        record = repo_root / "docs" / "releases" / f"{project.version}.md"
        require(record.is_file() and not record.is_symlink(), f"release record is required as a regular file: {record.relative_to(repo_root)}")
        require(record.resolve().is_relative_to(repo_root), "release record must remain inside the repository")
        require(not ignored(repo_root, record), "release record may not be ignored")
        tracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", str(record.relative_to(repo_root))],
            cwd=repo_root,
            check=False,
            capture_output=True,
        )
        require(tracked.returncode == 0, "release record must be tracked by Git")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", type=Path)
    parser.add_argument("--release", action="store_true")
    args = parser.parse_args()
    try:
        validate_source(args.repo, args.release)
    except SourceError as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    print(f"Validated package source: {args.repo.resolve()}")


if __name__ == "__main__":
    main()
