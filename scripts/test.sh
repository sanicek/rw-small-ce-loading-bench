#!/usr/bin/env bash
set -euo pipefail

# Keep local validation explicit and host-independent; no hosted CI is assumed.
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 -m unittest discover -s "$repo_root/tests" -v
