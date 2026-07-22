# Artwork Workflow

The tracked manifest defines prompts and exact game outputs. Credentials, raw
downloads, receipts, candidates, and review sheets stay outside this repository
in `rw-art-pipeline` state.

```bash
./scripts/artwork.sh prompt mod-icon
./scripts/artwork.sh auth scenario
./scripts/artwork.sh models gpt
./scripts/artwork.sh generate mod-icon --estimate-only
./scripts/artwork.sh generate mod-icon --confirm-cost
./scripts/artwork.sh select mod-icon 1
./scripts/artwork.sh approve mod-icon --replace
./scripts/artwork.sh validate

# Manual fallback
./scripts/artwork.sh intake mod-icon /path/to/source.png
./scripts/artwork.sh approve mod-icon --replace
```

Always show the complete dry-run batch cost and obtain explicit approval before
`--confirm-cost`. Present the generated candidate sheet and wait for an explicit
selection before `select` or `approve`. A general request for artwork approves
neither the charge nor a candidate.

The default sibling checkout is `../rw-art-pipeline`; set
`RW_ART_PIPELINE_DIR` to use another location. State defaults to
`~/.local/share/rw-art-pipeline/<package-id>` and can be overridden with
`RW_ART_STATE_DIR`. Scenario credentials come from `SCENARIO_API_KEY` and
`SCENARIO_API_SECRET` or the mode-0600 credential file created by `auth`.

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

## Loading-bench artwork

The release artwork composites the second concept in the top row of the
external `lb-proto.png` sheet onto the canonical base. The selected module
combines a compact powder hopper with a single loading press. The generated
sheet remains outside version control.

- Source SHA-256: `beae78c6aef9653b2c5fd70cbe09efbed1255329aacdc8dd15fa92534555adb7`
- Source crop: `(430,70)` through `(675,290)`
- Maximum fixture size: `64x56` on the `128x128` texture
- Placement: centered at `x=64`, bottom aligned to `y=90`
- Fixture treatment: gamma `0.65`, saturation `0.65`, 8-value color steps
- Detail treatment: half-resolution intermediate render, Gaussian blur `0.55`,
  deterministic low-frequency luminance noise with amplitude `5`
- Fixture mask: partial red `112`, matching vanilla electric-tailor fixtures
- Texture SHA-256: `06280e4a31a5a20644028a2a27405ee241e1a189f5d9d9600ceb398d1cc6b1e9`
- Mask SHA-256: `219035638caae1b08f673f6ed35bfc1f88e78e7570241630e05347f13f07e88f`

The compositor removes the light neutral concept-sheet background, preserves
the canonical bench pixels, and compresses the fixture's contrast, saturation,
and fine gradients into broader vanilla-style forms. Partial red mask values
let the fixture inherit some stuff color while the bench body remains fully
stuff-colored. Rebuild the artwork through the repository wrapper:

```bash
./scripts/artwork.sh prototype "$HOME/Downloads/ImageGen/lb-proto.png" \
  /tmp/opencode/loading-bench-blank.png \
  /tmp/opencode/loading-bench-blank_m.png \
  Textures/Things/Building/SmallCELoadingBench/LoadingBench.png \
  Textures/Things/Building/SmallCELoadingBench/LoadingBench_m.png \
  --crop 430,70,675,290 --maximum 64,56 --center-x 64 --bottom 90 \
  --detail-scale 0.5 --blur-radius 0.55 --noise-amplitude 5
```
