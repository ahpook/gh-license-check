# Project brief

> This document captures the goals and scope as originally prompted, so the
> intent behind the tool stays attached to the code.

## Why this exists

The Dependency Graph team specced a public API to validate a package's license
against a repository's license policy
([github/dependency-graph#13799](https://github.com/github/dependency-graph/pull/13799),
spec: `docs/specs/validate-packages-against-license-policy.md`). This repo is a
small `gh` CLI extension that consumes that API.

The motivating consumer is an AI coding agent:

> As an AI coding agent, I want to consume an API that validates a package's
> license against enterprise policy, so that I do not generate code or
> recommend usage of an open source library that violates the policy.

## Design choices

- **Python**, so it can be hand-edited alongside AI work. It runs as a `gh`
  extension via a small bash launcher (`gh-license-check`) that execs
  `python3 -m license_check`. Standard library only — no dependencies to
  install.
- The CLI calls the live API through `gh api`, so it reuses the user's `gh`
  authentication and host configuration. The repository defaults to the one in
  the current directory. A fixture-backed mock (`--mock`) remains for offline
  use and tests.
- **Fail-safe exit codes.** Unknown packages (PURLs that can't be evaluated)
  count as a failure by default (`--fail-on denied,unknown`), matching the
  argument that an agent should not proceed on packages it can't evaluate.

## Roadmap

1. **Single/few PURLs (done).** Accept one or more PURLs as arguments and
   validate them against the repository's policy through the live API. Began
   against a fixture-backed mock (a few real packages and a policy that permits
   only MIT) before the endpoint shipped.
2. **Next: SBOM input.** Accept an SPDX or CycloneDX document, extract PURLs
   with lib4sbom (Apache-2.0), and run them through the same check path. (The
   API defers SBOM support to async future work; this tool can extract PURLs
   client-side and reuse the synchronous package-checks endpoint, batching to
   stay under the API's apparent request-size limit.)
3. **Agent skill (done).** Package the tool as a skill an agent can call inside
   its coding loop, so it does not recommend or add packages that would violate
   the organization's license policy. See `skills/gh-license-check/SKILL.md`.

## Scope guardrails

- The mock is for offline development and tests. It mirrors the live API's
  response conventions but is not an SPDX expression evaluator, and its license
  data is illustrative.
- Results depend on the repository's policy and the caller's access to it, so
  live tests are opt-in (see the README).
