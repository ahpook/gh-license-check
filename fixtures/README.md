# Mock fixtures

These stand in for the not-yet-live `package-checks` API. The mock mirrors the
real two-stage design:

1. **`package_licenses.json`** — package → license. Stands in for Dependency
   Graph's `GetPackageMetadata`. Keys are exact PURLs; values are SPDX license
   expressions. A PURL that is absent here resolves to `unknown` (the API's
   "no license data" case).

2. **`policy.json`** — the repository's license policy. Stands in for the
   `osslicensecompliance` evaluator.
   - `allowed_licenses`: licenses permitted by policy.
   - `allowed_packages`: version-less `pkg:type/name` keys that are exempted —
     allowed regardless of license — producing an `allowed_package` result.

   > The feature is allow-list only. There is no package deny-list, so the
   > mock never produces a `denied_package` result (that reason is part of the
   > API enum but not implemented server-side today).

## What the demo data exercises

| PURL | License | Result | Reason |
| ---- | ------- | ------ | ------ |
| `pkg:npm/lodash@4.17.21` | MIT | allowed | `allowed_license` |
| `pkg:npm/left-pad@1.3.0` | WTFPL | denied | `denied_license` |
| `pkg:pypi/requests@2.31.0` | Apache-2.0 | denied | `denied_license` |
| `pkg:pypi/exemption@2.31.0` | GPL-3.0-only | allowed | `allowed_package` (exemption) |
| `pkg:npm/dual-licensed-pkg@1.0.0` | MIT OR Apache-2.0 | allowed | `allowed_license` |
| `pkg:npm/compound-pkg@2.0.0` | MIT AND Apache-2.0 | denied | `denied_license` |
| anything else | — | unknown | — |

> License strings are illustrative. `MIT` is used as the single allowed license
> because it is ubiquitous; swap in your own data to model a different policy.
