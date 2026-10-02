# API contract

Summary of the endpoint this tool consumes, from
`docs/specs/validate-packages-against-license-policy.md` in
[github/dependency-graph](https://github.com/github/dependency-graph) (merged
from PR #13799). The mock transport reproduces this shape locally.

> Status: the endpoint is **specced but not deployed**. Until it ships, use the
> mock (default). `--live` calls the real route via `gh api`.

## Route

```
POST /repos/:owner/:repo/license-compliance/package-checks
```

## Request body

```json
{
  "purls": [
    "pkg:npm/lodash@4.17.21",
    "pkg:pypi/requests@2.31.0"
  ]
}
```

| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| `purls` | array of strings | Yes | Package URLs to validate. |

The `purls` key is a wrapper so fields can be added later (e.g. a policy name)
without a breaking change.

## Response body

```json
{
  "purls": {
    "pkg:npm/lodash@4.17.21":   { "status": "allowed", "license": "MIT",          "reason": "allowed_license" },
    "pkg:pypi/requests@2.31.0": { "status": "denied",  "license": "Apache-2.0",   "reason": "denied_license" },
    "pkg:npm/unpublished@1.0.0":{ "status": "unknown", "license": null,           "reason": null }
  }
}
```

| Field | Values | Description |
| ----- | ------ | ----------- |
| `purls` | object | Keyed by the submitted PURL. |
| `.status` | `allowed`, `denied`, `unknown` | `unknown` = no license data or the PURL could not be parsed/evaluated. |
| `.license` | SPDX expression or `null` | The license evaluated against policy; `null` when `unknown`. |
| `.reason` | `allowed_license`, `allowed_package`, `denied_license`, `denied_package`, or `null` | Package-level exception vs. license-level decision; `null` when `unknown`. |

## Notes for consumers

- Results are keyed by the **exact** submitted PURL, so echo back what you sent.
- `unknown` is not "pass". A consumer that must avoid policy violations should
  treat `unknown` as a failure (this tool does so by default).
- SBOM (SPDX/CycloneDX) validation is explicitly **future work** on the API
  side and would be asynchronous (submit job, poll for results).
