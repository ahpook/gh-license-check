"""Transports: where package-check results actually come from.

The CLI talks to a `Transport` which, given a repo and a list of PURLs,
returns the API response body shape:

    {"purls": {"<purl>": {"status", "license", "reason"}}}

`MockTransport` evaluates against local fixtures and is the default while the
real endpoint is unimplemented. `GhApiTransport` shells out to `gh api` and is
ready for when the endpoint ships.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Dict, List

from . import models as m
from .purl import PurlError, package_key, parse_purl


class Transport:
    """Interface: resolve PURLs to per-package results for a repo."""

    def check(self, repo: str, purls: List[str]) -> dict:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Mock transport
# ---------------------------------------------------------------------------

_CONJUNCTION = re.compile(r"\s+AND\s+", re.IGNORECASE)
_DISJUNCTION = re.compile(r"\s+OR\s+", re.IGNORECASE)


class MockTransport(Transport):
    """Evaluate PURLs against local fixtures.

    Mirrors the real two-stage design:
      1. package -> license   (stands in for DG API / GetPackageMetadata)
      2. license -> policy    (stands in for OLC's evaluator)

    Fixtures (see fixtures/):
      package_licenses.json : {"<purl>": "<spdx-license>"}  (exact PURL match)
      policy.json           : allowed licenses + package exemptions

    The feature is allow-list only: `allowed_licenses` lists permitted
    licenses and `allowed_packages` lists package-level exemptions (allow a
    specific package regardless of license). There is no package deny-list, so
    the mock never produces a `denied_package` result.
    """

    def __init__(self, fixtures_dir: Path):
        self.fixtures_dir = Path(fixtures_dir)
        self.licenses: Dict[str, str] = _load_json(
            self.fixtures_dir / "package_licenses.json"
        )
        policy = _load_json(self.fixtures_dir / "policy.json")
        self.allowed_licenses = {
            lic.strip() for lic in policy.get("allowed_licenses", [])
        }
        self.allowed_packages = set(policy.get("allowed_packages", []))

    def check(self, repo: str, purls: List[str]) -> dict:
        results: Dict[str, dict] = {}
        for purl in purls:
            results[purl] = self._evaluate(purl).to_dict()
        return {"purls": results}

    def _evaluate(self, purl: str) -> m.PackageResult:
        # A malformed PURL can't be evaluated -> unknown.
        try:
            parse_purl(purl)
            key = package_key(purl)
        except PurlError:
            return m.PackageResult(m.STATUS_UNKNOWN, None, None)

        # No license data -> unknown (matches API: DG API had nothing).
        license_expr = self.licenses.get(purl)
        if license_expr is None:
            return m.PackageResult(m.STATUS_UNKNOWN, None, None)

        # Package-level exemptions take precedence: allow a specific package
        # regardless of its license. There is no package deny-list.
        if key in self.allowed_packages:
            return m.PackageResult(
                m.STATUS_ALLOWED, license_expr, m.REASON_ALLOWED_PACKAGE
            )

        if self._license_allowed(license_expr):
            return m.PackageResult(
                m.STATUS_ALLOWED, license_expr, m.REASON_ALLOWED_LICENSE
            )
        return m.PackageResult(m.STATUS_DENIED, license_expr, m.REASON_DENIED_LICENSE)

    def _license_allowed(self, expr: str) -> bool:
        """Shallow SPDX expression check.

        Enough for fixtures: `A AND B` needs every part allowed, `A OR B`
        needs any part allowed. Not a real SPDX expression evaluator.
        """
        expr = expr.strip().strip("()")
        if _CONJUNCTION.search(expr):
            return all(self._license_allowed(p) for p in _CONJUNCTION.split(expr))
        if _DISJUNCTION.search(expr):
            return any(self._license_allowed(p) for p in _DISJUNCTION.split(expr))
        return expr in self.allowed_licenses


def _load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"fixture not found: {path}")
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Real API transport (ready for when the endpoint is live)
# ---------------------------------------------------------------------------


class GhApiTransport(Transport):
    """Call the real endpoint through `gh api`, reusing the user's gh auth.

    Experimental: the endpoint is not deployed yet. Kept so switching to the
    live API is a flag, not a rewrite.
    """

    def __init__(self, hostname: str | None = None):
        self.hostname = hostname

    def check(self, repo: str, purls: List[str]) -> dict:
        if "/" not in repo:
            raise ValueError(f"--repo must be in OWNER/REPO form, got {repo!r}")
        path = f"repos/{repo}/license-compliance/package-checks"
        payload = json.dumps({"purls": purls})

        cmd = ["gh", "api", "--method", "POST", path, "--input", "-"]
        if self.hostname:
            cmd += ["--hostname", self.hostname]

        proc = subprocess.run(
            cmd, input=payload, capture_output=True, text=True
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"gh api call failed ({proc.returncode}): {proc.stderr.strip()}"
            )
        return json.loads(proc.stdout)
