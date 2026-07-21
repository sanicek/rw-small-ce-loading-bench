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
