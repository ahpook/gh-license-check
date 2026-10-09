---
name: gh-license-check
description: Check open source package licenses against the repository's license policy before adding, installing, or recommending a dependency. Use this whenever you are about to add a package to a manifest (package.json, requirements.txt, pyproject.toml, go.mod, Cargo.toml, Gemfile, pom.xml, *.csproj, etc.), run an install command (npm install, pip install, go get, cargo add, bundle add, etc.), suggest a library to the user, or when the user asks whether a package or license is allowed.
---

# License policy check

Use the `gh license-check` CLI to confirm that a package's license is allowed by the repository's license policy before you add or recommend it. The goal is to avoid generating code that depends on a library the organization does not permit.

## When to run it

Run the check before any of these actions (not after):

- Adding or upgrading a dependency in a manifest or lockfile.
- Running a package install command.
- Recommending a library in an answer or plan, including alternatives you propose.

You do not need to re-check packages that are already present in the manifest at the same version, unless the user asks.

## Prerequisites

1. Confirm the extension is available: `gh license-check --version`. If it is missing, ask the user before installing it with `gh extension install ahpook/gh-license-check`.
2. Determine the target repository: `gh repo view --json nameWithOwner -q .nameWithOwner`.

## Build PURLs

The CLI takes Package URLs. Always include an exact version, since the policy service looks up license data per version. If the user did not specify one, use the version you are about to pin; if you would install "latest", resolve it first (for example `npm view <name> version` or `pip index versions <name>`).

| Ecosystem | PURL form | Example |
| --- | --- | --- |
| npm | `pkg:npm/<name>@<ver>` (scoped: `pkg:npm/%40scope/<name>@<ver>`) | `pkg:npm/lodash@4.17.21` |
| PyPI | `pkg:pypi/<name>@<ver>` (lowercase, `_` becomes `-`) | `pkg:pypi/requests@2.31.0` |
| Go | `pkg:golang/<module path>@<ver>` | `pkg:golang/github.com/spf13/cobra@v1.8.0` |
| Cargo | `pkg:cargo/<name>@<ver>` | `pkg:cargo/serde@1.0.200` |
| RubyGems | `pkg:gem/<name>@<ver>` | `pkg:gem/rails@7.1.3` |
| Maven | `pkg:maven/<group>/<artifact>@<ver>` | `pkg:maven/org.apache.commons/commons-lang3@3.14.0` |
| NuGet | `pkg:nuget/<name>@<ver>` | `pkg:nuget/Newtonsoft.Json@13.0.3` |

## Run the check

Batch every candidate package into a single call and request JSON:

```sh
gh license-check --json --repo OWNER/REPO pkg:npm/lodash@4.17.21 pkg:pypi/requests@2.31.0
```

Exit codes: `0` means every package is allowed, `1` means at least one package is denied or unknown, and `2` means a usage or transport error (report it to the user and do not treat it as approval).

The response is keyed by the PURL you submitted:

```json
{
  "purls": {
    "pkg:npm/lodash@4.17.21": { "status": "allowed", "license": "MIT", "reason": "allowed_license" },
    "pkg:pypi/requests@2.31.0": { "status": "denied", "license": "Apache-2.0", "reason": "denied_license" }
  }
}
```

## Act on the result

| status | reason | What to do |
| --- | --- | --- |
| `allowed` | `allowed_license` | Proceed. |
| `allowed` | `allowed_package` | Proceed. The package is exempted by policy even though its license would not otherwise be allowed; mention this to the user. |
| `denied` | `denied_license` | Do not add, install, or recommend the package. Tell the user which license was found and that the policy does not allow it. Offer alternatives, and check those alternatives with this skill before suggesting them. |
| `unknown` | `null` | Do not proceed silently. There is no license data for that version (or the PURL could not be parsed). Recheck the PURL; if it is correct, tell the user and ask how they want to proceed. |

Never work around a denial (for example by vendoring the code, copying source from the package, or choosing a different version without checking it). If the user explicitly decides to proceed anyway, follow their decision and note that the package needs a policy exemption.

## Current limitation: mock data

The upstream API (`POST /repos/:owner/:repo/license-compliance/package-checks`) is not deployed yet. Until it is, the CLI evaluates against bundled fixture data, prints a notice on stderr, and ignores `--repo`. Results in this mode do not reflect the organization's real policy, so tell the user when your decision relied on mock results. Once the endpoint is live, add `--live` to call it through `gh api` with the user's credentials.

## Scope

The check covers only the packages you submit. It does not evaluate transitive dependencies, and it does not replace the dependency review that runs on pull requests.
