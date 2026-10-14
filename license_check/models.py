"""Data types mirroring the API contract.

Status and reason values are the exact strings returned by the REST API
(see docs/api-contract.md), so JSON round-trips without translation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# Status values returned per package.
STATUS_ALLOWED = "allowed"
STATUS_DENIED = "denied"
STATUS_UNKNOWN = "unknown"

# Reason values.
REASON_ALLOWED_LICENSE = "allowed_license"
REASON_ALLOWED_PACKAGE = "allowed_package"
REASON_DENIED_LICENSE = "denied_license"
# The API returns the string "unknown" (not null) alongside an unknown status.
REASON_UNKNOWN = "unknown"
# Defined by the API's reason enum, but the feature has no package deny-list,
# so the server does not produce this and the mock never emits it. Kept so
# response parsing stays complete if that changes.
REASON_DENIED_PACKAGE = "denied_package"

STATUSES = {STATUS_ALLOWED, STATUS_DENIED, STATUS_UNKNOWN}
REASONS = {
    REASON_ALLOWED_LICENSE,
    REASON_ALLOWED_PACKAGE,
    REASON_DENIED_LICENSE,
    REASON_DENIED_PACKAGE,
    REASON_UNKNOWN,
}


@dataclass(frozen=True)
class Coordinate:
    """A package identity extracted from a PURL."""

    package_manager: str
    package_name: str
    package_version: Optional[str]


@dataclass(frozen=True)
class PackageResult:
    """Per-PURL outcome, matching `purls.<purl>` in the response body."""

    status: str
    license: Optional[str]
    reason: Optional[str]

    @classmethod
    def from_dict(cls, data: dict) -> "PackageResult":
        return cls(
            status=data.get("status", STATUS_UNKNOWN),
            license=data.get("license"),
            reason=data.get("reason"),
        )

    def to_dict(self) -> dict:
        return {"status": self.status, "license": self.license, "reason": self.reason}
