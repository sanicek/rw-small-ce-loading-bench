# Design

## Purpose

Combat Extended's loading bench occupies a 3x1 footprint. Small CE Loading Bench
will reduce that existing workstation to 2x1 for compact workshops without
changing what the bench crafts or introducing a replacement building.

## Runtime model

The initial package is declarative XML loaded from the repository root after
Combat Extended on RimWorld 1.6. The planned implementation will patch CE's
existing `AmmoBench` Def rather than creating a parallel Def, preserving bills,
recipes, work givers, research integration, and references from other mods.

No gameplay patch is present during repository bootstrap. The final dimensions,
graphic draw size, interaction cell, placement behavior, and occupied-cell
visuals must be verified together when implementation begins.

## Durable contracts

Treat the following as compatibility-sensitive once published:

- RimWorld package ID
- Def names and inheritance
- Translation keys referenced from code
- Serialized settings and save keys
- Component and class names persisted in saves
- Supported RimWorld version folders
- Combat Extended's `AmmoBench` identity and bill ownership

Prefer additions and migrations over renaming or reinterpreting persisted
identity. A deliberate break requires a major version and explicit update risk.

## Integration decisions

Combat Extended is a required dependency and must load first. The intended
change is a RimWorld XML patch against `AmmoBench`; it should require neither a
compile reference nor Harmony. Any expansion beyond that declarative scope must
be justified and approved under `AGENTS.md`.

## Failure behavior

RimWorld's dependency metadata prevents normal activation without Combat
Extended. If CE changes or removes `AmmoBench`, the patch should fail visibly in
the startup log rather than create a partially compatible replacement.
