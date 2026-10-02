"""Minimal Package URL (PURL) parsing.

We only need the pieces the API cares about: type (package manager), name,
and version. This is a deliberately small parser covering the common
`pkg:type/namespace/name@version` shape rather than the full PURL spec.
"""

from __future__ import annotations

from urllib.parse import unquote

from .models import Coordinate


class PurlError(ValueError):
    """Raised when a string is not a parseable PURL."""


def parse_purl(purl: str) -> Coordinate:
    """Parse a PURL string into a Coordinate.

    Examples:
        pkg:npm/lodash@4.17.21              -> (npm, lodash, 4.17.21)
        pkg:npm/@babel/core@7.0.0           -> (npm, @babel/core, 7.0.0)
        pkg:pypi/requests@2.31.0?foo=bar    -> (pypi, requests, 2.31.0)
    """
    if not isinstance(purl, str) or not purl.strip():
        raise PurlError("PURL is empty")

    raw = purl.strip()
    if not raw.startswith("pkg:"):
        raise PurlError(f"PURL must start with 'pkg:': {purl!r}")

    body = raw[len("pkg:"):]

    # Strip subpath (#...) and qualifiers (?...); we don't use them.
    body = body.split("#", 1)[0]
    body = body.split("?", 1)[0]

    if "/" not in body:
        raise PurlError(f"PURL is missing a type/name separator: {purl!r}")

    ptype, remainder = body.split("/", 1)
    ptype = ptype.strip().lower()
    if not ptype:
        raise PurlError(f"PURL is missing a type: {purl!r}")

    version = None
    if "@" in remainder:
        remainder, version = remainder.rsplit("@", 1)
        version = unquote(version) or None

    name = unquote(remainder.strip("/"))
    if not name:
        raise PurlError(f"PURL is missing a name: {purl!r}")

    return Coordinate(package_manager=ptype, package_name=name, package_version=version)


def package_key(purl: str) -> str:
    """Return the version-less `pkg:type/name` key, for policy exceptions."""
    coord = parse_purl(purl)
    return f"pkg:{coord.package_manager}/{coord.package_name}"
