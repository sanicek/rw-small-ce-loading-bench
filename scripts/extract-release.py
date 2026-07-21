#!/usr/bin/env python3
"""Preflight and extract one locally produced release archive."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from release_archive import ArchiveError, extract_release

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("package_name")
    args = parser.parse_args()
    try:
        extract_release(args.archive, args.destination, args.package_name)
    except (ArchiveError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
