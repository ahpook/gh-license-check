"""Data types mirroring the API contract.

Status and reason values are the exact strings used by the public REST API
(see docs/api-contract.md), so JSON round-trips without translation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# Status values returned per package.
STATUS_ALLOWED = "allowed"
STATUS_DENIED = "denied"
STATUS_UNKNOWN = "unknown"

# Reason values. `null` (None) accompanies an unknown status.
REASON_ALLOWED_LICENSE = "allowed_license"
REASON_ALLOWED_PACKAGE = "allowed_package"
REASON_DENIED_LICENSE = "denied_license"
# Defined by the API's reason enum, but the feature has no package deny-list
# today, so the server does not currently produce this and the mock never
# emits it. Kept for complete response parsing if that changes.
REASON_DENIED_PACKAGE = "denied_package"


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
