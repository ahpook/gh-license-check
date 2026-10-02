"""gh-license-check: validate package licenses against a repo's policy.

Thin client over the Dependency Graph "validate packages against license
policy" API:

    POST /repos/:owner/:repo/license-compliance/package-checks

The API is not live yet, so by default we evaluate against local fixtures
through an in-process mock transport. A `gh api` transport is included for
when the real endpoint ships.
"""

__version__ = "0.1.0"
