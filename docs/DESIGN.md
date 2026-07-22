# Design

## Purpose

Combat Extended's loading bench occupies a 3x1 footprint. Small CE Loading Bench
reduces that existing workstation to 1x1 for compact workshops without
changing what the bench crafts or introducing a replacement building.

## Runtime model

The package is declarative XML loaded from the repository root after Combat
Extended on RimWorld 1.6. It patches CE's existing `AmmoBench` Def rather than
creating a parallel Def, preserving bills, recipes, work givers, research
integration, and references from other mods.

The bench follows RimWorld's engine-native `DeepDrill` presentation pattern: a
rotatable one-cell Def uses `Graphic_Single` with `drawRotated` and `allowFlip`
disabled. Placement rotation therefore moves the inherited interaction cell
without rotating or mirroring the fixed south-facing pseudo-perspective art.
The first visual phase uses rw-art's symmetric cube workbench at draw size
`(1.17,1.5)`. The width is one third of vanilla's 3.5-wide butcher-table
presentation, while the retained 1.5 height gives the one-cell graphic normal
worktable overhang. This evaluates scale, alignment, fixed perspective, and
stuff recoloring before adding loading-specific tools.

`CutoutComplex` maps the stuff-derived primary color to the mask's red channel.
The green channel receives the Def's static secondary color, keeping the work
surface neutral while the frame and apron reflect steel, wood, or another valid
stuff material.

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
change is a RimWorld XML patch against `AmmoBench`; it requires neither a
compile reference nor Harmony. Any expansion beyond that declarative scope must
be justified and approved under `AGENTS.md`.

## Failure behavior

RimWorld's dependency metadata prevents normal activation without Combat
Extended. If CE changes or removes `AmmoBench`, the patch should fail visibly in
the startup log rather than create a partially compatible replacement.
