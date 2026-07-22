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

## Workbench template trial

Phase one uses the approved `generic-cube-workbench-1x1` runtime texture and
recolor mask from rw-art commit
`804a5631f666f8e48fe1a1c9b41be2f1ab138009`:

- Texture SHA-256: `4da3b2b9a06ccac1a879da532946ff28f79120280bd41cbff10c6467c9794fad`
- Mask SHA-256: `75aae84875fe21129a39f2aa9e4ca571339cacdfb495fbeb489889111138fa0c`

Export templates through this repository's wrapper:

```bash
./scripts/artwork.sh templates export generic-cube-workbench-1x1 rimworld-texture Textures/Things/Building/SmallCELoadingBench/LoadingBench.png
./scripts/artwork.sh templates export generic-cube-workbench-1x1 rimworld-color-mask Textures/Things/Building/SmallCELoadingBench/LoadingBench_m.png
```

The cube uses a square `(1.5,1.5)` draw mesh, matching the engine-native drill
pattern so horizontal placement rotations cannot swap its dimensions. Its
`96x104` visible bounds preserve the one-cell width while matching the shallower
profile of standard worktables. The plain top and apron share one stuff-color
channel; there is no separate white surface or decorative frame. It is
intentionally still a blank base; project-specific tools follow only after its
in-game scale and recoloring pass.
