#!/usr/bin/env bash
set -euo pipefail

# Installation is transactional: validate before moving the current mod, then
# restore it if placement or byte comparison fails.

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
metadata="$repo_root/About/About.xml"
python3 "$repo_root/scripts/validate-source.py" "$repo_root"
package_name="$(python3 "$repo_root/scripts/project.py" "$metadata" package-name)"
mod_version="$(python3 "$repo_root/scripts/project.py" "$metadata" version)"
rimworld_input="${RIMWORLD_DIR:-${HOME:?HOME must be set}/.local/share/Steam/steamapps/common/RimWorld}"
artifact_dir="$repo_root/artifacts/$package_name"
release_dir="$repo_root/artifacts/releases"
install_release=false
stage_dir=""
stage_parent=""
release_extract_dir=""
backup_dir=""
old_target_moved=false
new_target_placed=false
commit_completed=false

if [[ $# -gt 1 || ( $# -eq 1 && "$1" != "--release" ) ]]; then
    printf 'Usage: %s [--release]\n' "$0" >&2
    exit 2
fi
[[ $# -eq 1 ]] && install_release=true

canonical_dir() {
    if [[ ! -d "$1" ]]; then
        printf 'Error: required directory does not exist: %s\n' "$1" >&2
        exit 1
    fi
    realpath -e -- "$1"
}

cleanup() {
    local status=$?
    trap - EXIT
    set +e
    [[ -n "$stage_parent" && -d "$stage_parent" ]] && rm -rf -- "$stage_parent"
    [[ -z "$stage_parent" && -n "$stage_dir" && -d "$stage_dir" ]] && rm -rf -- "$stage_dir"
    [[ -n "$release_extract_dir" && -d "$release_extract_dir" ]] && rm -rf -- "$release_extract_dir"
    if [[ "$commit_completed" != true ]]; then
        [[ "$new_target_placed" == true && ( -e "$target_dir" || -L "$target_dir" ) ]] && rm -rf -- "$target_dir"
        if [[ "$old_target_moved" == true && -n "$backup_dir" && ( -e "$backup_dir" || -L "$backup_dir" ) && ! -e "$target_dir" && ! -L "$target_dir" ]]; then
            mv -T -- "$backup_dir" "$target_dir"
        fi
    fi
    exit "$status"
}

rimworld_dir="$(canonical_dir "$rimworld_input")"
mods_dir="$(canonical_dir "$rimworld_dir/Mods")"
target_dir="$mods_dir/$package_name"
exec 9<"$mods_dir"
if ! flock -n 9; then
    printf 'Error: another mod installation is in progress in %s.\n' "$mods_dir" >&2
    exit 1
fi
if [[ -L "$target_dir" ]]; then
    printf 'Error: refusing to replace symlinked install target: %s\n' "$target_dir" >&2
    exit 1
fi
if [[ -e "$target_dir" ]]; then
    existing_metadata="$target_dir/About/About.xml"
    if [[ ! -f "$existing_metadata" ]]; then
        printf 'Error: existing target is not an identifiable %s installation: %s\n' "$package_name" "$target_dir" >&2
        exit 1
    fi
    existing_package_id="$(python3 "$repo_root/scripts/project.py" "$existing_metadata" package-id)"
    incoming_package_id="$(python3 "$repo_root/scripts/project.py" "$metadata" package-id)"
    if [[ "$existing_package_id" != "$incoming_package_id" ]]; then
        printf 'Error: install target belongs to %s, not %s.\n' "$existing_package_id" "$incoming_package_id" >&2
        exit 1
    fi
fi
trap cleanup EXIT

mkdir -p -- "$repo_root/artifacts"
exec 8<"$repo_root/artifacts"
flock 8

if [[ "$install_release" == false ]]; then
    ARTIFACT_LOCK_HELD=1 "$repo_root/scripts/build.sh"
    stage_parent="$(mktemp -d -- "$mods_dir/.$package_name.stage.XXXXXX")"
    stage_dir="$stage_parent/$package_name"
    mkdir -- "$stage_dir"
    cp -a -- "$artifact_dir/." "$stage_dir/"
else
    archive="$release_dir/$package_name-v$mod_version.zip"
    checksum="$archive.sha256"
    if [[ ! -f "$archive" || ! -f "$checksum" ]]; then
        printf 'Error: --release requires %s and its .sha256 file.\n' "$archive" >&2
        exit 1
    fi
    (cd "$release_dir" && sha256sum -c "$(basename "$checksum")")
    release_extract_dir="$(mktemp -d -- "$mods_dir/.$package_name.release.XXXXXX")"
    python3 "$repo_root/scripts/extract-release.py" "$archive" "$release_extract_dir" "$package_name"
    stage_dir="$release_extract_dir/$package_name"
fi
python3 "$repo_root/scripts/validate-package.py" "$stage_dir" --rimworld-dir "$rimworld_dir"
python3 "$repo_root/scripts/validate-mod.py" "$stage_dir"
staged_metadata="$stage_dir/About/About.xml"
staged_package_id="$(python3 "$repo_root/scripts/project.py" "$staged_metadata" package-id)"
staged_version="$(python3 "$repo_root/scripts/project.py" "$staged_metadata" version)"
incoming_package_id="$(python3 "$repo_root/scripts/project.py" "$metadata" package-id)"
if [[ "$staged_package_id" != "$incoming_package_id" || "$staged_version" != "$mod_version" ]]; then
    printf 'Error: staged package identity/version does not match source metadata.\n' >&2
    exit 1
fi

if [[ -e "$target_dir" || -L "$target_dir" ]]; then
    backup_dir="$(mktemp -d -- "$mods_dir/.$package_name.backup.XXXXXX")"
    rmdir -- "$backup_dir"
    old_target_moved=true
    mv -T -- "$target_dir" "$backup_dir"
fi
mv -T -- "$stage_dir" "$target_dir"
new_target_placed=true
stage_dir=""
if [[ -n "$stage_parent" ]]; then
    rmdir -- "$stage_parent"
    stage_parent=""
fi
if [[ "$install_release" == false ]]; then
    diff -r -- "$artifact_dir" "$target_dir"
else
    rmdir -- "$release_extract_dir"
    release_extract_dir=""
fi

commit_completed=true
trap - EXIT
[[ -n "$backup_dir" ]] && rm -rf -- "$backup_dir"
printf 'Success: installed %s at %s\n' "$package_name" "$target_dir"
