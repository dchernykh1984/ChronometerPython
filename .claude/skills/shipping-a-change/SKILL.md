---
name: shipping-a-change
description: The path from a change to a merged PR in this repository - branching, one-line conventional commits, the local gate, gh, the six CI checks, and how a release is cut. Use whenever asked to fix, implement, or open a pull request here.
---

# Shipping a change

## The loop

1. Branch off `main` (fetch first). Branch names follow the commit type:
   `fix/...`, `feat/...`, `chore/...`, `ci/...`, `docs/...`, `refactor/...`.
2. Implement in **separate commits, one per concern**.
3. Re-read the diff fresh before pushing - see the `reviewing-a-change` skill.
4. Run the local gate (see the `local-gate` skill). Do not push red.
5. Push and open the PR with `gh`.
6. Hand the PR link back. **Do not merge** unless merging was asked for. The
   author writes in Russian and the difference between asking for a pull
   request and asking for a release is one word - re-read the request.

## Commit messages

Single-line conventional commits. **No body, no trailers, and never a
`Co-Authored-By` line or any Claude attribution** - the same goes for PR
bodies. `.claude/settings.json` already blanks both attributions, so nothing
should append them; if one appears, strip it.

```
fix: keep the group start time after saving a group
test: share the qt window fixture through a conftest
ci: cap the build job runtime with a timeout
```

`cz check --rev-range origin/main..HEAD` runs on every PR, so a message that
does not parse fails CI. `feat:` and `fix:` drive the release-please version
bump; `chore:`, `ci:`, `docs:`, `test:`, `refactor:` do not.

Merges to `main` are done with **rebase**, so every commit subject you write
ends up in the public history and in the changelog. Write them for that reader.

## Opening the PR

```
git push -u origin <branch>
gh pr create --title "<plain sentence, no type prefix>" --body "<what and why>"
```

PR titles in this repo read as plain sentences ("Keep the group start time
after saving a group"); the conventional prefix lives in the commits.

## The checks

Six run on every PR. Watch them in a loop rather than by repeated manual calls:

```
gh pr checks <N> --json name,bucket --jq '.[] | "\(.bucket)\t\(.name)"' | sort
```

Take the verdict from the rollup, not from that list: `gh pr checks` reports a
per-check status that lags and can still say `pending` long after the job has
finished, which reads like a hung check.

```
gh pr view <N> --json statusCheckRollup \
  --jq '[.statusCheckRollup[] | {name:(.name//.context), s:(.conclusion//.state)}]'
```

| Check | What it does |
| --- | --- |
| `pre-commit` | The whole pre-commit config on all files. |
| `commitizen` | `cz check` over `origin/main..HEAD`. |
| `tests` | `uv run pytest` on Linux with the Qt runtime libs installed. |
| `audit` | `pip-audit` over the exported runtime dependencies. |
| `build / targets` | Computes the build matrix. |
| `build / build (ubuntu-22.04, linux-x86_64)` | PyInstaller smoke build. |

## Releasing

Only when explicitly asked. release-please opens a `chore(main): release X.Y.Z`
PR after conventional commits land on `main`; merging it cuts the tag, syncs
`uv.lock` to the new version, builds the portable apps for every platform and
attaches them to the GitHub release. Never bump `pyproject.toml` by hand.

Confirm the assets landed:

```
gh release view vX.Y.Z --json assets --jq '.assets[].name'
```

## Reporting back

Lead with the conclusion: what changed, what the user has to do differently,
and anything found but deliberately left alone. Skip the derivation unless it
changes what they do next.
