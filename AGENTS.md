# AGENTS.md

## Project conventions

- Keep generated builds, package artifacts, and local RimWorld files out of
  version control.
- Validate package structure with `python3 scripts/validate-package.py <package>`.
- Do not add Workshop publication identifiers until a page has been published.
- Treat `About/About.xml` `modVersion` as the single release version. Tags and
  GitHub releases use the matching `vMAJOR.MINOR.PATCH` form.
- Any change that alters the generated installable package or runtime behavior
  is release-bearing. The same pull request must select the next Semantic
  Version, update `modVersion`, add its release record, and complete the
  release-candidate workflow before merge.
- Repository-only documentation, process, tests, and tooling changes need no
  version bump when generated package output is unchanged. Tooling that changes
  package output is release-bearing.

## Engineering guardrails

- Prefer the simplest engine-native or declarative solution. Do not introduce a
  workaround whose implementation complexity, compatibility risk, or upkeep is
  disproportionate to the issue without explicit user approval.
- Before requesting approval for a complex workaround, explain the underlying
  issue, mechanism, implementation cost, compatibility risks, and simpler
  alternatives. A general request to fix an issue is not approval.
- Any new or materially expanded Harmony patch requires explicit user approval.
  Explain why XML, inheritance, composition, or a supported public API cannot
  solve the problem; identify the target and patch type; and justify scope and
  compatibility risk.
- Existing Harmony patches accepted in completed phases remain approved unless
  their targets, scope, or behavior materially change.

## Artwork workflow

- Follow `artwork/README.md` and use `scripts/artwork.sh`, not ad hoc generation
  or image processing.
- Keep credentials, raw generations, receipts, candidates, and review sheets
  outside version control. Only explicitly approved outputs enter `Textures/`
  or `About/`.
- Show the Scenario dry-run batch cost and obtain explicit user approval before
  paid generation. A general request for art is not charge approval.
- Present the configured candidate sheet and do not select or promote an option
  until the user explicitly chooses it.
- Validate approved artwork and package output before committing.

## Literate programming

- Write maintained code as a top-down narrative that introduces each file and
  nontrivial phase before implementation.
- Keep explanations next to the code they govern. Document intent, invariants,
  lifecycle, compatibility constraints, failure behavior, and non-obvious
  tradeoffs rather than restating syntax.
- Document public entry points and divide multiphase scripts and validators into
  named conceptual phases. Prefer clear names over compensating comments.
- Remove dead code instead of preserving it in comments. Keep comments and
  maintainer documentation accurate when workflows, package layout, supported
  versions, or validation rules change.
- Do not add narrative comments to generated files, lockfiles, binaries,
  artwork, vendored content, or checksum-frozen recovered artifacts.

## Validation workflow

- Run `scripts/test.sh` and `scripts/install-local.sh` after gameplay changes so
  the package is built, validated, and installed for testing.
- The user performs one lightweight representative RimWorld smoke test after
  installation. Do not expand it into an exhaustive QA matrix without request.
- Do not merge a release-bearing pull request until the user confirms that the
  exact release-candidate smoke test passed. Record confirmation in the release
  record and pull request; update durable design documentation when accepted
  behavior is a compatibility contract.
- Documentation-only and process-only changes require only affected validation.
- Keep validation local. Do not add hosted CI services unless policy changes.

## Git workflow

- `main` is protected and must never receive direct commits or pushes. All
  changes go through feature branches.
- Create branches from `main` with `feat/`, `fix/`, `chore/`, `refactor/`, or
  `docs/` and a short kebab-case description.
- For release-bearing changes, choose the next version under
  `docs/RELEASES.md`, update `About/About.xml`, and add the matching release
  record on the same branch.
- Validate, stage only intended files, and commit with a Conventional Commits
  message.
- Push the branch and create a pull request. Use a draft PR while a
  release-bearing change awaits its smoke test.
- If changes are requested, reuse the branch, validate, commit, and push.
- After smoke-test confirmation, update the release record and PR body, mark the
  PR ready, then ask whether it is ready to merge.
- Before merging, inspect the clean worktree, every PR commit, and the complete
  diff from `main`. No hosted checks are expected.
- Merge with `gh pr merge --merge --delete-branch`, synchronize local `main`,
  remove the local branch, and prune the remote.

## Release workflow

- Keep releases local and operator-driven.
- Increment `modVersion` exactly once from the latest published version. Use
  PATCH for compatible fixes, MINOR for backward-compatible functionality, and
  MAJOR for intentional compatibility breaks.
- Record exact RimWorld, dependency, source, and tool versions in the candidate.
- From a clean candidate commit, run `python3 scripts/package-release.py`, then
  `scripts/install-local.sh --release` and the representative smoke test.
- Record the candidate checksum and never publish an untested package.
- After acceptance and merge, synchronize clean `main`, rebuild, and require the
  checksum to match. A mismatch requires another install and smoke test.
- Merge approval for an accepted release-bearing PR also authorizes its
  post-merge annotated tag and GitHub release, unless checksum verification
  fails.
- Publish the installable ZIP, checksum, and release record. GitHub-generated
  source archives are not installable RimWorld packages.
- Add `PublishedFileId.txt` only after the Workshop page exists; Workshop upload
  remains a separate explicit publication step.
