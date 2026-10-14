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
2. The policy comes from a repository. By default the CLI uses the repository in the current directory. If you are working outside a clone, or the user names a different repository, pass `--repo OWNER/REPO`.

## Build PURLs

The CLI takes Package URLs. Always include an exact version, since the policy service looks up license data per version. If the user did not specify one, use the version you are about to pin; if you would install "latest", resolve it first (for example `npm view <name> version` or `pip index versions <name>`).

| Ecosystem | PURL form | Example |
| --- | --- | --- |
| npm | `pkg:npm/<name>@<ver>` (scoped: `pkg:npm/@scope/<name>@<ver>`; `%40scope` also works) | `pkg:npm/lodash@4.17.21` |
| PyPI | `pkg:pypi/<name>@<ver>` (lowercase, `_` becomes `-`) | `pkg:pypi/requests@2.31.0` |
| Go | `pkg:golang/<module path>@<ver>` | `pkg:golang/github.com/spf13/cobra@v1.8.0` |
| Cargo | `pkg:cargo/<name>@<ver>` | `pkg:cargo/serde@1.0.200` |
| RubyGems | `pkg:gem/<name>@<ver>` | `pkg:gem/rails@7.1.3` |
| Maven | `pkg:maven/<group>/<artifact>@<ver>` | `pkg:maven/org.apache.commons/commons-lang3@3.14.0` |
| NuGet | `pkg:nuget/<name>@<ver>` | `pkg:nuget/Newtonsoft.Json@13.0.3` |

## Run the check

Batch every candidate package into a single call and request JSON:

```sh
gh license-check --json pkg:npm/lodash@4.17.21 pkg:npm/@cosmicdrift/kumiko-types@0.351.0
```

Exit codes: `0` means every package is allowed, `1` means at least one package is denied or unknown, and `2` means a usage or API error. An error is never approval. Report it to the user; the message on stderr explains the cause. A 404 means the repository doesn't exist, the user can't read its license policy, or license compliance isn't enabled for it (for example, a personal repository), so the check can't be done there.

The response is keyed by the PURL you submitted:

```json
{
  "purls": {
    "pkg:npm/lodash@4.17.21": { "status": "allowed", "license": "MIT", "reason": "allowed_license" },
    "pkg:npm/@cosmicdrift/kumiko-types@0.351.0": { "status": "denied", "license": "BUSL-1.1", "reason": "denied_license" }
  }
}
```

## Act on the result

| status | license | reason | What to do |
| --- | --- | --- | --- |
| `allowed` | any | `allowed_license` | Proceed. |
| `allowed` | any | `allowed_package` | Proceed. The package is exempted by policy even though its license may not otherwise be allowed; mention this to the user. |
| `denied` | an SPDX expression | `denied_license` | Do not add, install, or recommend the package. Tell the user which license was found and that the policy does not allow it. Offer alternatives, and check those alternatives with this skill before suggesting them. |
| `denied` | `null` | `denied_license` | Do not proceed. There is no license data for that package version, and policy only allows known licenses. Double-check the name and version (a typo produces this result); if they are correct, tell the user the license is unknown and ask how they want to proceed. |
| `unknown` | `null` | `unknown` | The PURL could not be evaluated, usually because the version is missing or the string is not a valid PURL. Fix the PURL and check again. |

Never work around a denial (for example by vendoring the code, copying source from the package, or choosing a different version without checking it). If the user explicitly decides to proceed anyway, follow their decision and note that the package needs a policy exemption.

## Scope

The check covers only the packages you submit. It does not evaluate transitive dependencies, and it does not replace the dependency review that runs on pull requests.
