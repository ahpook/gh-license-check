# gh-license-check

A [GitHub CLI](https://cli.github.com) extension that validates a package's
license against a repository's license policy, via the Dependency Graph
["validate packages against license policy" API](docs/api-contract.md).

Built for AI coding agents and developers who want a quick pre-flight check —
"before I add this dependency, is its license allowed here?" — without opening a
pull request.

> **Status:** early scaffold. The upstream API is specced but **not deployed
> yet**, so by default this evaluates against local fixtures through an
> in-process mock. See [docs/project-brief.md](docs/project-brief.md).

## Install

```sh
gh extension install ahpook/gh-license-check    # once published
# or, for local development from a clone:
gh extension install .
```

Requires `python3` on your `PATH`. No Python dependencies (standard library
only).

## Usage

Check a single package:

```sh
gh license-check pkg:npm/lodash@4.17.21
```

```
✓ ALLOWED pkg:npm/lodash@4.17.21
            license: MIT   reason: allowed_license
```

Check several at once, and get machine-readable output:

```sh
gh license-check --json \
  pkg:npm/lodash@4.17.21 \
  pkg:pypi/requests@2.31.0 \
  pkg:npm/some-unpublished-pkg@1.0.0
```

### Options

| Flag | Description |
| ---- | ----------- |
| `--repo OWNER/REPO` | Target repository (informational for the mock; required for `--live`). |
| `--json` | Emit the raw API response body. |
| `--fail-on LIST` | Statuses that cause a non-zero exit. Default `denied,unknown`. Use `denied` to ignore unknowns. |
| `--fixtures DIR` | Use a different mock fixtures directory. |
| `--live` | Call the real endpoint via `gh api` instead of the mock (not deployed yet). |
| `--hostname HOST` | GitHub hostname for `--live` (e.g. GHES). |

### Exit codes

- `0` — no package hit the `--fail-on` set.
- `1` — at least one package did (e.g. denied, or unknown by default).
- `2` — usage or transport error.

`unknown` is treated as a failure by default: a package with no license data
can't be shown to satisfy policy, so an agent should not proceed on it.

## How it works

The real API resolves each PURL in two stages — package → license (Dependency
Graph), then license → policy decision (osslicensecompliance). The mock mirrors
that with two fixtures (package licenses, policy). See
[fixtures/README.md](fixtures/README.md) and
[docs/api-contract.md](docs/api-contract.md).

```
gh license-check  ->  license_check.cli  ->  Transport
                                              ├─ MockTransport  (fixtures, default)
                                              └─ GhApiTransport (`gh api`, --live)
```

## Agent skill

[`skills/gh-license-check/SKILL.md`](skills/gh-license-check/SKILL.md) teaches a coding agent (Copilot CLI and other tools that read `SKILL.md`) to run this check before it adds, installs, or recommends a dependency, and how to act on each result.

Install the extension first, then make the skill visible to your agent. For all your projects, link it into your personal skills directory:

```sh
gh extension install ahpook/gh-license-check
mkdir -p ~/.copilot/skills
ln -s ~/.local/share/gh/extensions/gh-license-check/skills/gh-license-check ~/.copilot/skills/gh-license-check
```

(`gh` installs extensions under `${XDG_DATA_HOME:-~/.local/share}/gh/extensions/`. Linking means `gh extension upgrade` also updates the skill.)

For a single repository, copy the folder into that repo as `.github/skills/gh-license-check/`. In Copilot CLI, run `/skills reload` and confirm it appears in `/skills list`.

## Development

```sh
python3 -m unittest discover -s tests      # run tests
python3 -m license_check pkg:npm/lodash@4.17.21   # run without gh
```

## Roadmap

1. Single/few PURLs against policy (done).
2. Agent skill for in-loop license gating (done, see above).
3. SBOM input (SPDX and CycloneDX) using lib4sbom: extract PURLs and check them.

See [docs/project-brief.md](docs/project-brief.md) for the full brief.
