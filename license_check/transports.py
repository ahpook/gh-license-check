"""Transports: where package-check results come from.

The CLI talks to a `Transport` which, given a repo and a list of PURLs,
returns the API response body shape:

    {"purls": {"<purl>": {"status", "license", "reason"}}}

`GhApiTransport` calls the REST API through `gh api` (the default).
`MockTransport` evaluates against local fixtures, for offline use and tests.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Callable, Dict, List, Optional

from . import models as m
from .purl import PurlError, package_key, parse_purl

Runner = Callable[..., subprocess.CompletedProcess]


class Transport:
    """Interface: resolve PURLs to per-package results for a repo."""

    def check(self, repo: str, purls: List[str]) -> dict:
        raise NotImplementedError


class ApiError(RuntimeError):
    """A non-success response from the API (or from gh itself)."""

    def __init__(self, message: str, status: Optional[int] = None):
        super().__init__(message)
        self.status = status


# ---------------------------------------------------------------------------
# REST API transport
# ---------------------------------------------------------------------------

_HTTP_STATUS = re.compile(r"\(HTTP (\d{3})\)")

_HINTS = {
    401: "authentication failed; run `gh auth status`",
    403: "access denied; your token may lack permission to read this "
    "repository's license policy",
    404: "the repository was not found, you cannot read its license policy, "
    "or license compliance is not enabled for it",
    503: "the service could not complete the check; large batches can time "
    "out, so try fewer PURLs or retry later",
}


class GhApiTransport(Transport):
    """Call `POST /repos/{owner}/{repo}/license-compliance/package-checks`
    through `gh api`, reusing the user's gh authentication."""

    def __init__(self, hostname: Optional[str] = None, runner: Runner = subprocess.run):
        self.hostname = hostname
        self._run = runner

    def check(self, repo: str, purls: List[str]) -> dict:
        if repo.count("/") != 1 or not all(repo.split("/")):
            raise ValueError(f"repository must be OWNER/REPO, got {repo!r}")

        cmd = [
            "gh", "api", "--method", "POST",
            f"repos/{repo}/license-compliance/package-checks",
            "--input", "-",
        ]
        if self.hostname:
            cmd += ["--hostname", self.hostname]

        proc = self._run(
            cmd, input=json.dumps({"purls": purls}), capture_output=True, text=True
        )
        if proc.returncode != 0:
            raise _api_error(proc)
        return json.loads(proc.stdout)


def _api_error(proc: subprocess.CompletedProcess) -> ApiError:
    """Build a readable error from a failed `gh api` call.

    On HTTP errors gh prints the JSON error body on stdout and
    `gh: <message> (HTTP <status>)` on stderr.
    """
    status: Optional[int] = None
    message = ""
    try:
        body = json.loads(proc.stdout)
        message = body.get("message", "")
        status = int(body["status"]) if "status" in body else None
    except (ValueError, TypeError, KeyError):
        pass

    stderr = (proc.stderr or "").strip()
    if status is None:
        match = _HTTP_STATUS.search(stderr)
        if match:
            status = int(match.group(1))
    if not message:
        message = stderr.removeprefix("gh: ") or f"gh exited with {proc.returncode}"

    hint = _HINTS.get(status)
    prefix = f"HTTP {status}: " if status else ""
    text = f"{prefix}{message.strip()}"
    if hint:
        text += f" ({hint})"
    return ApiError(text, status)


def current_repo(runner: Runner = subprocess.run) -> str:
    """Return OWNER/REPO for the repository in the current directory."""
    cmd = ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"]
    proc = runner(cmd, capture_output=True, text=True)
    repo = (proc.stdout or "").strip()
    if proc.returncode != 0 or not repo:
        raise ValueError(
            "could not determine the repository from the current directory; "
            "pass --repo OWNER/REPO"
        )
    return repo


# ---------------------------------------------------------------------------
# Mock transport
# ---------------------------------------------------------------------------

_CONJUNCTION = re.compile(r"\s+AND\s+", re.IGNORECASE)
_DISJUNCTION = re.compile(r"\s+OR\s+", re.IGNORECASE)


class MockTransport(Transport):
    """Evaluate PURLs against local fixtures, mirroring the live API.

    Two stages, like the real service:
      1. package -> license   (Dependency Graph license data)
      2. license -> policy    (license policy evaluator)

    Fixtures (see fixtures/):
      package_licenses.json : {"<purl>": "<spdx-license>"}  (exact PURL match)
      policy.json           : allowed licenses + package exemptions

    Policy is allow-list only: `allowed_licenses` lists permitted licenses and
    `allowed_packages` exempts specific packages regardless of license. There
    is no package deny-list, so `denied_package` is never produced.
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
        return {"purls": {purl: self._evaluate(purl).to_dict() for purl in purls}}

    def _evaluate(self, purl: str) -> m.PackageResult:
        # A PURL that can't be parsed into a versioned package -> unknown.
        try:
            coord = parse_purl(purl)
            key = package_key(purl)
        except PurlError:
            coord = None
        if coord is None or not coord.package_version:
            return m.PackageResult(m.STATUS_UNKNOWN, None, m.REASON_UNKNOWN)

        license_expr = self.licenses.get(
            f"pkg:{coord.package_manager}/{coord.package_name}@{coord.package_version}",
            self.licenses.get(purl),
        )

        # Exemptions allow a package regardless of its license.
        if key in self.allowed_packages:
            return m.PackageResult(
                m.STATUS_ALLOWED, license_expr, m.REASON_ALLOWED_PACKAGE
            )

        # Like the live API, a package with no license data is denied (with a
        # null license), since a missing license isn't on the allow list.
        if license_expr is not None and self._license_allowed(license_expr):
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
