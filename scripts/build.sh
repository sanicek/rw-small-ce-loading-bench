#!/usr/bin/env bash
set -euo pipefail

# Build recreates a disposable package from a small game-facing allowlist. An
# XML-only mod needs no local game installation; copying a project into Source/
# activates the optional compilation phase and its RimWorld reference checks.

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
metadata="$repo_root/About/About.xml"
python3 "$repo_root/scripts/validate-source.py" "$repo_root"
mkdir -p -- "$repo_root/artifacts"
if [[ "${ARTIFACT_LOCK_HELD:-}" != "1" ]]; then
    exec 8<"$repo_root/artifacts"
    flock 8
fi
package_name="$(python3 "$repo_root/scripts/project.py" "$metadata" package-name)"
mod_version="$(python3 "$repo_root/scripts/project.py" "$metadata" version)"
read -r -a versions <<<"$(python3 "$repo_root/scripts/project.py" "$metadata" supported-versions)"
artifact_dir="$repo_root/artifacts/$package_name"

canonical_dir() {
    if [[ ! -d "$1" ]]; then
        printf 'Error: required directory does not exist: %s\n' "$1" >&2
        exit 1
    fi
    realpath -e -- "$1"
}

# Phase 1: compile the one opted-in project, if present. The explicit output
# directory avoids coupling package assembly discovery to a target framework.
shopt -s nullglob
projects=("$repo_root"/Source/*/*.csproj)
shopt -u nullglob
if (( ${#projects[@]} > 1 )); then
    printf 'Error: expected at most one Source/*/*.csproj, found %d.\n' "${#projects[@]}" >&2
    exit 1
fi
if (( ${#projects[@]} == 1 && ${#versions[@]} > 1 )); then
    printf 'Error: C# builds support one RimWorld version; configure per-version compilation before declaring more.\n' >&2
    exit 1
fi

built_dll=""
assembly_name=""
rimworld_dir=""
if (( ${#projects[@]} == 1 )); then
    rimworld_input="${RIMWORLD_DIR:-${HOME:?HOME must be set}/.local/share/Steam/steamapps/common/RimWorld}"
    rimworld_dir="$(canonical_dir "$rimworld_input")"
    managed_dir="$(canonical_dir "$rimworld_dir/RimWorldLinux_Data/Managed")"
    project="${projects[0]}"
    project_dir="$(dirname "$project")"
    assembly_name="$(python3 -c 'import sys, xml.etree.ElementTree as ET; p=sys.argv[1]; r=ET.parse(p).getroot(); print((r.findtext(".//AssemblyName") or __import__("pathlib").Path(p).stem).strip())' "$project")"
    build_output="$repo_root/artifacts/build/"
    rm -rf -- "$build_output"
    rm -rf -- "$project_dir/bin" "$project_dir/obj"
    dotnet restore "$project" --locked-mode
    dotnet build "$project" --configuration Release --no-restore -p:ModVersion="$mod_version" -p:RimWorldManagedDir="$managed_dir" -p:OutputPath="$build_output"
    built_dll="$build_output/$assembly_name.dll"
    if [[ ! -f "$built_dll" ]]; then
        printf 'Error: build output is missing: %s\n' "$built_dll" >&2
        exit 1
    fi
fi

# Phase 2: package only maintained runtime content. Optional directories and
# notices are copied when present, while source, docs, scaffolds, and local state
# can never leak into the installable artifact.
rm -rf -- "$artifact_dir"
mkdir -p -- "$artifact_dir"
content_dirs=(About Biomes Common Defs Languages Patches Sounds Textures)
for name in "${content_dirs[@]}"; do
    [[ -d "$repo_root/$name" ]] && cp -a -- "$repo_root/$name" "$artifact_dir/"
done
content_files=(LoadFolders.xml LICENSE THIRD_PARTY_NOTICES.md)
for name in "${content_files[@]}"; do
    [[ -f "$repo_root/$name" ]] && cp -- "$repo_root/$name" "$artifact_dir/$name"
done
for version in "${versions[@]}"; do
    if [[ -d "$repo_root/$version" ]]; then
        mkdir -p -- "$artifact_dir/$version"
        cp -a -- "$repo_root/$version/." "$artifact_dir/$version/"
        rm -f -- "$artifact_dir/$version/.gitkeep"
    fi
    if [[ -n "$built_dll" ]]; then
        mkdir -p -- "$artifact_dir/$version/Assemblies"
        cp -- "$built_dll" "$artifact_dir/$version/Assemblies/$assembly_name.dll"
    fi
done

# Phase 3: validate exactly what will be installed. Supplying RimWorld is
# optional for XML-only builds and adds only a local version diagnostic.
validator_args=("$artifact_dir")
[[ -n "$rimworld_dir" ]] && validator_args+=(--rimworld-dir "$rimworld_dir")
python3 "$repo_root/scripts/validate-package.py" "${validator_args[@]}"
python3 "$repo_root/scripts/validate-mod.py" "$artifact_dir"
printf 'Success: packaged %s %s at %s\n' "$(python3 "$repo_root/scripts/project.py" "$metadata" name)" "$mod_version" "$artifact_dir"
