# Mock fixtures

These back `--mock`, which evaluates PURLs locally for offline use and tests.
The mock mirrors the live API's two-stage design and its response conventions
(see [docs/api-contract.md](../docs/api-contract.md)):

1. **`package_licenses.json`** — package → license. Stands in for Dependency
   Graph's license data. Keys are PURLs (the type is matched
   case-insensitively); values are SPDX license expressions. A versioned PURL
   that is absent here is denied with a `null` license, as the live API does
   for packages with no license data.

2. **`policy.json`** — the repository's license policy. Stands in for the
   `osslicensecompliance` evaluator.
   - `allowed_licenses`: licenses permitted by policy.
   - `allowed_packages`: version-less `pkg:type/name` keys that are exempted —
     allowed regardless of license — producing an `allowed_package` result.

   > Policy is allow-list only. There is no package deny-list, so neither the
   > API nor the mock produces `denied_package`.

## What the demo data exercises

| PURL | License | Result | Reason |
| ---- | ------- | ------ | ------ |
| `pkg:npm/lodash@4.17.21` | MIT | allowed | `allowed_license` |
| `pkg:npm/left-pad@1.3.0` | WTFPL | denied | `denied_license` |
| `pkg:pypi/requests@2.31.0` | Apache-2.0 | denied | `denied_license` |
| `pkg:pypi/exemption@2.31.0` | GPL-3.0-only | allowed | `allowed_package` (exemption) |
| `pkg:npm/dual-licensed-pkg@1.0.0` | MIT OR Apache-2.0 | allowed | `allowed_license` |
| `pkg:npm/compound-pkg@2.0.0` | MIT AND Apache-2.0 | denied | `denied_license` |
| any other versioned PURL | `null` | denied | `denied_license` |
| `pkg:npm/lodash` (no version), `not-a-purl` | `null` | unknown | `unknown` |

> License strings are illustrative. `MIT` is used as the single allowed license
> because it is ubiquitous; swap in your own data to model a different policy.
