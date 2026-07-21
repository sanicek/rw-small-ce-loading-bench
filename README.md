# Small CE Loading Bench

Small CE Loading Bench is a RimWorld 1.6 compatibility mod intended to reduce
Combat Extended's loading bench from a 3x1 footprint to a compact 2x1 footprint
without replacing the bench or changing its recipes. The repository is
currently bootstrapped for development; the gameplay patch is not implemented
yet.

## Planned Behavior

- Adjust Combat Extended's existing `AmmoBench` through a declarative XML patch.
- Preserve the original Def identity, recipes, bills, research requirement, and
  work-giver integration.
- Avoid C# and Harmony unless engine-native patching proves insufficient.

## Requirements

- RimWorld 1.6
- [Combat Extended](https://github.com/CombatExtended-Continued/CombatExtended)

## Package Layout

- `About/`, `Defs/`, `Languages/`, and later `Textures/` are maintained game content.
- `scripts/build.sh` recreates `artifacts/<package-name>` from an allowlist.
- `scripts/validate-package.py` checks generic package contracts.
- `scaffolds/csharp/` is excluded from packages until copied to root `Source/`.
- `artwork/` owns prompts and output contracts; raw generations remain outside
  Git.
- `docs/releases/` records exact release candidates and smoke-test acceptance.

## Build And Install

An XML-only build needs Bash and Python 3.11 or newer:

```bash
scripts/test.sh
scripts/build.sh
scripts/install-local.sh
```

`install-local.sh` defaults to
`~/.local/share/Steam/steamapps/common/RimWorld`. Set `RIMWORLD_DIR` for another
installation. It stages and validates the replacement before moving the current
installed mod, and restores the prior directory if installation fails.

The optional C# scaffold additionally requires the .NET SDK and RimWorld's
managed assemblies. Follow `scaffolds/csharp/README.md` to opt in.

## Dependency

`About/About.xml` declares Combat Extended as required and loads this mod after
it. Development uses the configured `CombatExtended` checkout as a source
reference; no dependency files are redistributed.

## Releases

`About/About.xml` `modVersion` is the single release version. Compatible fixes
increment PATCH, backward-compatible features increment MINOR, and intentional
save, settings, Def identity, or supported-version breaks increment MAJOR.

See `docs/RELEASES.md` for the local release-candidate, checksum, smoke-test,
merge, tag, and GitHub release workflow. Hosted CI/CD is intentionally absent.

## Artwork

See `artwork/README.md`. Paid generation always requires a dry-run cost estimate
and explicit approval, followed by explicit user selection from the configured
candidate sheet. Only approved game-ready PNGs enter the tracked package tree.

## License

Small CE Loading Bench and the included Sanicek maker badge are available under
the MIT license. Add `THIRD_PARTY_NOTICES.md` whenever redistributed content
requires attribution or carries a different license.
