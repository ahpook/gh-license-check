"""gh-license-check: validate package licenses against a repo's policy.

Thin client over the Dependency Graph package-checks API:

    POST /repos/{owner}/{repo}/license-compliance/package-checks

Calls the API through `gh api` by default. `--mock` evaluates against local
fixtures instead, for offline use and tests.
"""

__version__ = "0.2.0"
