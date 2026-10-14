"""Command-line interface for gh-license-check.

Usage:
    gh license-check pkg:npm/lodash@4.17.21

Checks one or more PURLs against a repository's license policy and prints a
verdict per package. Exit code is non-zero when any package fails the
`--fail-on` set, so it can gate an agent or CI loop.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List

from . import __version__
from . import models as m
from .transports import GhApiTransport, MockTransport, current_repo

# Default fixtures ship alongside the package (repo-root/fixtures).
_DEFAULT_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"

_SYMBOL = {
    m.STATUS_ALLOWED: "✓",
    m.STATUS_DENIED: "✗",
    m.STATUS_UNKNOWN: "?",
}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="gh license-check",
        description="Validate package licenses against a repository's policy.",
    )
    p.add_argument("purls", nargs="*", help="One or more Package URLs (PURLs).")
    p.add_argument(
        "-R",
        "--repo",
        default=None,
        help="Repository whose policy to check against, as OWNER/REPO "
        "(default: the repository in the current directory).",
    )
    p.add_argument(
        "--hostname",
        default=None,
        help="GitHub hostname to call (e.g. a GHES or ghe.com host).",
    )
    p.add_argument(
        "--mock",
        action="store_true",
        help="Evaluate against local fixtures instead of calling the API "
        "(offline use and testing).",
    )
    p.add_argument(
        "--fixtures",
        type=Path,
        default=_DEFAULT_FIXTURES,
        help="Fixtures directory for --mock (default: bundled fixtures/).",
    )
    p.add_argument(
        "--fail-on",
        default="denied,unknown",
        help="Comma-separated statuses that cause a non-zero exit "
        "(default: denied,unknown). Use 'denied' to ignore unknowns.",
    )
    p.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit the raw API response body as JSON.",
    )
    # Accepted for compatibility with earlier versions, where the API call
    # was opt-in. It is now the default.
    p.add_argument("--live", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv: List[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if not args.purls:
        print("error: provide at least one PURL to check", file=sys.stderr)
        return 2

    fail_on = {s.strip() for s in args.fail_on.split(",") if s.strip()}

    try:
        if args.mock:
            transport = MockTransport(args.fixtures)
            repo = args.repo or "OWNER/REPO"
            print(
                f"note: --mock evaluates against fixtures in {args.fixtures}, "
                "not a real repository policy",
                file=sys.stderr,
            )
        else:
            transport = GhApiTransport(hostname=args.hostname)
            repo = args.repo or current_repo()
        response = transport.check(repo, args.purls)
    except Exception as exc:  # surface setup and transport failures cleanly
        print(f"error: {exc}", file=sys.stderr)
        return 2

    results = response.get("purls", {})

    if args.as_json:
        print(json.dumps(response, indent=2))
    else:
        _print_table(args.purls, results)

    failed = any(
        results.get(purl, {}).get("status", m.STATUS_UNKNOWN) in fail_on
        for purl in args.purls
    )
    return 1 if failed else 0


def _print_table(purls: List[str], results: dict) -> None:
    for purl in purls:
        result = results.get(purl, {})
        status = result.get("status", m.STATUS_UNKNOWN)
        license_ = result.get("license") or "-"
        reason = result.get("reason") or "-"
        symbol = _SYMBOL.get(status, "?")
        print(f"{symbol} {status.upper():7} {purl}")
        print(f"            license: {license_}   reason: {reason}")
