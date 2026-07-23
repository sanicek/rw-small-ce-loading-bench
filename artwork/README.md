# Artwork Workflow

The tracked manifest defines exact game-output contracts. Reusable source
artwork comes from rw-art's versioned template catalog, while prototype source
sheets remain outside this repository.

```bash
./scripts/artwork.sh templates export sanicek-s-logo rimworld-mod-icon About/ModIcon.png --replace
./scripts/artwork.sh validate
```

The default sibling checkout is `../rw-art-pipeline`; set
`RW_ART_PIPELINE_DIR` to use another location.

## Canonical mod icon

The mod icon uses rw-art's standalone `sanicek-s-logo` template rather than a
project-specific generated badge. The `rimworld-mod-icon` variant is a
transparent `256x256` RGBA PNG whose exact SHA-256 is
`6d8d16106c8c3154db2b927c56368038698e3d55d56c55dc6c5ac29ad7744327`.
Rebuild it through the repository wrapper using the export command above.

## Canonical workbench template

The accepted blank base uses rw-art's canonical `generic-cube-workbench-1x1`
runtime texture and recolor mask from merge commit
`5fcd6a7a398adfcacdd064836cf3e36f0a99e7c7`. These exact hashes identify the
accepted template independently of checkout location:

- Texture SHA-256: `3dd636662abd3032c2989dc7305f9e2e62982701cdb47ab28976e6bc05f50a1f`
- Mask SHA-256: `3abf5f5fc20e76e9c7e55dc1ca41dd31ac39e2948f5ab425cbba8177541a1adc`

Export templates through this repository's wrapper:

```bash
./scripts/artwork.sh templates export generic-cube-workbench-1x1 rimworld-texture Textures/Things/Building/SmallCELoadingBench/LoadingBench.png
./scripts/artwork.sh templates export generic-cube-workbench-1x1 rimworld-color-mask Textures/Things/Building/SmallCELoadingBench/LoadingBench_m.png
```

The cube uses a square `(1.5,1.5)` draw mesh, matching the engine-native drill
pattern so horizontal placement rotations cannot swap its dimensions. Its
`92x103` visible bounds preserve the one-cell width while matching the shallower
profile of standard worktables. The plain top and apron share one stuff-color
channel. A darker apron meets the light top directly, following vanilla
worktables by defining the front edge through tone rather than a black divider.
There is no separate white surface or decorative frame. It is
intentionally a blank base for adding project-specific tools. rw-art's
`reference-assets/generic-cube-workbench-1x1/ThingDef.xml` records the complete
RimWorld XML setup used for its accepted in-game appearance.

## About-page preview

The mod information page uses a deterministic title card rather than generated
art. Its `1234x500` RGB canvas follows RimWorld's recommended `2.468:1` preview
ratio. The background is pure black, the exact mod name is centered at the top
in white DejaVu Sans Condensed Bold, and the accepted runtime texture is centered
below it at `256x256` with nearest-neighbor scaling. The texture's primary mask
channel is composited with the documented steel approximation `(160,178,181)`.
Combat Extended's canonical `300x100` compatibility badge is placed unscaled in
the lower-left corner with a 32-pixel margin.

The title font is identified by SHA-256
`586556501565e46ad356a5efcc2f6e81375230323ad5a2a1c4cc8211a6c5ef2e`.
Compose and intake the review candidate through the repository wrapper; do not
write directly to `About/Preview.png`:

```bash
./scripts/artwork.sh preview /path/to/CombatExtended/Media/Badge_CE_compatible.png \
  /tmp/opencode/small-ce-loading-bench-preview.png
./scripts/artwork.sh intake about-preview /tmp/opencode/small-ce-loading-bench-preview.png
```

After visual approval, promote it with `./scripts/artwork.sh approve
about-preview`. The approved `About/Preview.png` SHA-256 is
`1eb77eaa21db5bf10eb01bed59732c18157662e3a74d85a048f2386cd918b7f7`.

## Loading-bench artwork

The release artwork cleans an externally reviewed, positioned loading-press
composition and places its fixture over the canonical base. The source remains
outside version control.

- Source SHA-256: `f63a6e54dfcedd33f107973c62f606401406e9c66c6d1b474a3c4c82e715c065`
- Cleanup crop: `(37,25)` through `(101,94)`
- Fixture treatment: preserve authored scale, position, color, and shading;
  discard neutral pixels at luminance `185` and above, unmatte the `170`-`185`
  anti-alias band, and retain only the connected fixture assembly
- Fixture mask: partial red `112`, matching vanilla electric-tailor fixtures
- Texture SHA-256: `d0c6a2a685ca4f97081e2b12fd3cffefdfe80280ddb65fe195ef172297bbb66d`
- Mask SHA-256: `0fd5cb99b3d04901aa56bb92928454f7b106ededbf6ae1d101d5c3b027de76f3`

The positioned-source cleanup removes the light neutral rectangle and its pale
anti-aliased fringe without rescaling or moving the fixture. Disconnected marks
and pixels identified as backing reveal the canonical base underneath; retained
fixture coverage receives a partial red mask so it inherits some stuff color
while the base remains fully stuff-colored. Rebuild the artwork through the
repository wrapper:

```bash
./scripts/artwork.sh prototype "$HOME/Pictures/LoadingBench.png" \
  /tmp/opencode/loading-bench-blank.png \
  /tmp/opencode/loading-bench-blank_m.png \
  Textures/Things/Building/SmallCELoadingBench/LoadingBench.png \
  Textures/Things/Building/SmallCELoadingBench/LoadingBench_m.png \
  --crop 37,25,101,94 --positioned-source
```
