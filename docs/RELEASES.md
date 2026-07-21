# Release Policy

## Versioning

The mod uses Semantic Versioning. `About/About.xml` is the single source for the
current version. Local builds pass it to optional assemblies, release archives
include it in their names, and Git tags use `vMAJOR.MINOR.PATCH`.

- PATCH contains compatible fixes or packaging corrections.
- MINOR adds backward-compatible gameplay or user-facing functionality.
- MAJOR changes a save, setting, Def identity, or other compatibility contract,
  or drops an already supported RimWorld series.

Dependency revisions in a release record are known-good build and smoke-test
baselines, not a promise that external dependencies remain pinned.

## Release records

Copy `docs/releases/EXAMPLE.md` to `docs/releases/MAJOR.MINOR.PATCH.md`. Each
published version's record also serves as GitHub release notes and records
changes, update risks, exact build dependencies, source revision, archive
checksum, and representative smoke-test result.

## Local publication workflow

1. Update `modVersion` and add the release record on a feature branch.
2. Validate and commit the candidate so the worktree is clean.
3. Run `python3 scripts/package-release.py`.
4. Run `scripts/install-local.sh --release` so testing uses the exact ZIP.
5. Complete the representative smoke test and record its checksum and result.
6. Commit acceptance, push, and merge through the pull-request workflow.
7. Synchronize clean `main`, rebuild, and require the checksum to match.
8. Create and push the annotated version tag.
9. Publish the ZIP, checksum, and release record with `gh release create`.

The attached `<PackageName>-vMAJOR.MINOR.PATCH.zip` is installable. GitHub's
automatically generated source archives are repository snapshots, not packages.
