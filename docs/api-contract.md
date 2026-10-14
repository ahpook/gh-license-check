# API contract

The endpoint this tool calls was specified in
`docs/specs/validate-packages-against-license-policy.md` in
[github/dependency-graph](https://github.com/github/dependency-graph) (from
PR #13799). This page records the behavior observed from the live API, which
differs from the spec in a few places (see below).

## Route

```
POST /repos/{owner}/{repo}/license-compliance/package-checks
```

The tool calls it through `gh api`, so it uses your existing `gh`
authentication. The repository determines which license policy applies.

## Request body

```json
{
  "purls": [
    "pkg:npm/lodash@4.17.21",
    "pkg:npm/@cosmicdrift/kumiko-types@0.351.0"
  ]
}
```

| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| `purls` | array of strings | Yes | Package URLs to validate. At least one is required. |

The `purls` key is a wrapper so fields can be added later (for example a
policy name) without a breaking change.

## Response body

Results are keyed by the exact PURL string submitted.

```json
{
  "purls": {
    "pkg:npm/lodash@4.17.21":                    { "status": "allowed", "license": "MIT",       "reason": "allowed_license" },
    "pkg:npm/postgres@3.4.9-kumiko.1":           { "status": "allowed", "license": "Unlicense", "reason": "allowed_package" },
    "pkg:npm/@cosmicdrift/kumiko-types@0.351.0": { "status": "denied",  "license": "BUSL-1.1",  "reason": "denied_license" },
    "pkg:npm/does-not-exist-zzz@0.0.1":          { "status": "denied",  "license": null,        "reason": "denied_license" },
    "pkg:npm/lodash":                            { "status": "unknown", "license": null,        "reason": "unknown" }
  }
}
```

| Field | Values | Description |
| ----- | ------ | ----------- |
| `purls` | object | Keyed by the submitted PURL. |
| `.status` | `allowed`, `denied`, `unknown` | The policy decision for the package. |
| `.license` | SPDX expression or `null` | The license evaluated against policy. `null` when there is no license data or the PURL could not be evaluated. |
| `.reason` | `allowed_license`, `allowed_package`, `denied_license`, `unknown` | Whether the decision came from the license or from a package exemption. |

A recorded response lives in [`tests/data/live_response.json`](../tests/data/live_response.json).

### Observed behavior that differs from the spec

- `unknown` results carry `"reason": "unknown"` (a string). The spec showed
  `null`.
- A well-formed, versioned PURL for a package with no license data is
  `denied` with `"license": null` and `"reason": "denied_license"`. The spec
  described this case as `unknown`. In practice `unknown` is returned only for
  PURLs that can't be evaluated (not a PURL, or no version).
- Policy is allow-list only, so `denied_package` (listed in the spec's enum)
  is not produced.
- The PURL type is case-insensitive (`pkg:NPM/...` resolves like `pkg:npm/...`).

## Errors

| HTTP status | When |
| ----------- | ---- |
| 404 | The repository doesn't exist, the caller can't read its license policy, or license policy isn't available for it (a personal repository returned 404). |
| 422 | Invalid body, for example an empty `purls` array. |
| 503 | The check could not complete. A request with 1,001 PURLs returned 503 while 101 succeeded, so very large batches appear to time out. |

No maximum batch size is documented yet.

## Notes for consumers

- Echo back the PURL you sent to look up its result.
- `unknown` is not a pass. A consumer that must avoid policy violations should
  treat it as a failure (this tool does so by default).
- A `denied` result with a `null` license means there was no license data for
  that version, which is a different conversation with the user than a known
  disallowed license.
- SBOM (SPDX/CycloneDX) validation is future work on the API side and is
  planned to be asynchronous (submit a job, poll for results).
