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
`da429ef63720c034a96403954fccd4b28bd7aefa`:

- Texture SHA-256: `fc3aff67a72a181a35b0dffcccce36a8d14632ddeb47a5cb594e5944421750a2`
- Mask SHA-256: `d04af9edf226198dbf6dca48571a1b0055f28766e97ee4ff943ff6021da68785`

Export templates through this repository's wrapper:

```bash
./scripts/artwork.sh templates export generic-cube-workbench-1x1 rimworld-texture Textures/Things/Building/SmallCELoadingBench/LoadingBench.png
./scripts/artwork.sh templates export generic-cube-workbench-1x1 rimworld-color-mask Textures/Things/Building/SmallCELoadingBench/LoadingBench_m.png
```

The cube uses a square `(1.5,1.5)` draw mesh, matching the engine-native drill
pattern so horizontal placement rotations cannot swap its dimensions. Its
`96x118` visible bounds preserve the approved one-cell width and standard
worktable height inside that square canvas. It is intentionally still a blank
base; project-specific tools follow only after its in-game scale and recoloring
pass.
