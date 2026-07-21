#!/usr/bin/env bash
set -euo pipefail

# The shared toolkit owns provider and processing logic; this repository owns
# prompts and approved outputs. Override paths for non-sibling checkouts.
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
pipeline_dir="${RW_ART_PIPELINE_DIR:-$repo_root/../rw-art-pipeline}"
manifest="$repo_root/artwork/manifest.toml"

if [[ ! -f "$pipeline_dir/rw_art_pipeline/__main__.py" ]]; then
    printf 'Error: rw-art-pipeline not found at %s; set RW_ART_PIPELINE_DIR.\n' "$pipeline_dir" >&2
    exit 1
fi
if [[ $# -lt 1 ]]; then
    printf 'Usage: %s {templates|prompt|auth|models|generate|select|intake|approve|reject|validate} [arguments...]\n' "$0" >&2
    exit 2
fi

global_args=()
[[ -n "${RW_ART_STATE_DIR:-}" ]] && global_args+=(--state-dir "$RW_ART_STATE_DIR")
if [[ "$1" == "templates" ]]; then
    PYTHONPATH="$pipeline_dir" exec python3 -P -m rw_art_pipeline templates "${@:2}"
fi
PYTHONPATH="$pipeline_dir" exec python3 -P -m rw_art_pipeline "${global_args[@]}" "$1" "$manifest" "${@:2}"
