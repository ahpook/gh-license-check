# gh-license-check

A [GitHub CLI](https://cli.github.com) extension that checks packages against a
repository's license policy, using the Dependency Graph
[package-checks API](docs/api-contract.md).

It's built for AI coding agents and developers who want a quick pre-flight check
("before I add this dependency, is its license allowed here?") without opening a
pull request.

## Install

```sh
gh extension install ahpook/gh-license-check
```

Requires `python3` on your `PATH`. There are no Python dependencies (standard
library only).

## Usage

Run it inside a clone of the repository whose policy you want to check against,
or name the repository with `--repo`:

```sh
gh license-check --repo OWNER/REPO \
  pkg:npm/postgres@3.4.9-kumiko.1 \
  pkg:npm/@cosmicdrift/kumiko-types@0.351.0
```

```
✓ ALLOWED pkg:npm/postgres@3.4.9-kumiko.1
            license: Unlicense   reason: allowed_package
✗ DENIED  pkg:npm/@cosmicdrift/kumiko-types@0.351.0
            license: BUSL-1.1   reason: denied_license
```

Add `--json` for the raw API response, which is what an agent or script should
parse.

Each PURL needs an exact version. A PURL without a version (or a string that
isn't a PURL) comes back `unknown`.

### Options

| Flag | Description |
| ---- | ----------- |
| `-R`, `--repo OWNER/REPO` | Repository whose policy applies. Defaults to the repository in the current directory. |
| `--json` | Emit the raw API response body. |
| `--fail-on LIST` | Statuses that cause a non-zero exit. Default `denied,unknown`. Use `denied` to ignore unknowns. |
| `--hostname HOST` | GitHub host to call (for example a GHES or ghe.com host). |
| `--mock` | Evaluate against local fixtures instead of calling the API (offline use and testing). |
| `--fixtures DIR` | Fixtures directory for `--mock`. |

### Exit codes

- `0`: no package hit the `--fail-on` set.
- `1`: at least one package did (denied, or unknown by default).
- `2`: usage or API error, such as a 404 when license compliance isn't
  enabled for the repository or you can't read its policy.

`unknown` is treated as a failure by default, since a package that couldn't be
evaluated hasn't been shown to satisfy policy.

## How it works

The API resolves each PURL in two stages: package to license (Dependency Graph
data), then license to a policy decision. A package with no license data is
denied with a `null` license. See [docs/api-contract.md](docs/api-contract.md)
for the observed contract, including where it differs from the original spec.

```
gh license-check  ->  license_check.cli  ->  Transport
                                              ├─ GhApiTransport (`gh api`, default)
                                              └─ MockTransport  (fixtures, --mock)
```

The mock mirrors the same two stages with two fixture files. See
[fixtures/README.md](fixtures/README.md).

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
python3 -m unittest discover -s tests                 # offline tests
python3 -m license_check --mock pkg:npm/lodash@4.17.21  # run without gh or network
```

The offline suite covers PURL parsing, the mock, the `gh api` transport (with a
fake `gh`), and the CLI against a response recorded from the live API.

Tests against the live API are opt-in, because results depend on a
repository's policy and on your access to it. Point them at a repository whose
policy you can read:

```sh
GH_LICENSE_CHECK_LIVE_REPO=OWNER/REPO python3 -m unittest tests.test_live -v
```

By default these only assert behavior that holds under any policy. To also pin
verdicts for your repository, set `GH_LICENSE_CHECK_LIVE_EXPECT` to a JSON map
of PURL to status, for example
`'{"pkg:npm/lodash@4.17.21": "allowed"}'`. See `tests/test_live.py`.

## Roadmap

1. Single/few PURLs against policy (done).
2. Agent skill for in-loop license gating (done, see above).
3. SBOM input (SPDX and CycloneDX) using lib4sbom: extract PURLs and check them.

See [docs/project-brief.md](docs/project-brief.md) for the full brief.
