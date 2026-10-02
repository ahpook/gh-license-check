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
- **The API is not live yet**, so by default we evaluate against local
  fixtures through an in-process mock (`MockTransport`). The client has a clean
  transport seam; a `gh api`-based transport (`GhApiTransport`) is already in
  place for when the endpoint ships (`--live`).
- **Fail-safe exit codes.** Unknown packages (no license data / unparseable)
  count as a failure by default (`--fail-on denied,unknown`), matching the
  argument that an agent should not proceed on packages it can't evaluate.

## Roadmap

1. **Now — single/few PURLs (done).** Accept one or more PURLs as arguments and
   validate against the mock policy. Fixtures hold a few real packages with
   license strings and a simple policy that permits only MIT.
2. **Next — SBOM (SPDX) input.** Accept an SPDX document, extract PURLs from it,
   and run them through the same check path. (The real API defers SBOM support
   to async future work; this tool can extract PURLs client-side and reuse the
   synchronous package-checks endpoint.)
3. **Later — agent skill.** Package the tool as a skill an agent can call inside
   its coding loop, so it does not recommend or add packages that would violate
   the organization's license policy.

## Scope guardrails

- The mock is for local development only; it is not an SPDX expression
  evaluator and its license data is illustrative.
- When the real endpoint is live, the mock remains useful for offline tests and
  for shaping fixtures that mirror a given policy.
