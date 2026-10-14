"""Opt-in tests against the live API.

Skipped unless GH_LICENSE_CHECK_LIVE_REPO is set to an OWNER/REPO whose
license policy your gh credentials can read:

    GH_LICENSE_CHECK_LIVE_REPO=octo/repo python3 -m unittest tests.test_live -v

Verdicts depend on that repository's policy, so by default these tests only
assert behavior that holds under any policy. To also pin expected verdicts
for your repository, set GH_LICENSE_CHECK_LIVE_EXPECT to a JSON object
mapping PURLs to statuses, for example:

    GH_LICENSE_CHECK_LIVE_EXPECT='{"pkg:npm/lodash@4.17.21": "allowed"}'

Set GH_LICENSE_CHECK_LIVE_HOSTNAME to target a host other than github.com.
"""

import json
import os
import unittest

from license_check import models as m
from license_check.transports import ApiError, GhApiTransport

REPO = os.environ.get("GH_LICENSE_CHECK_LIVE_REPO")
HOSTNAME = os.environ.get("GH_LICENSE_CHECK_LIVE_HOSTNAME") or None
EXPECT = json.loads(os.environ.get("GH_LICENSE_CHECK_LIVE_EXPECT") or "{}")

# Policy-independent probes: license data is a property of the package, and
# unparseable or versionless PURLs can't be evaluated under any policy.
WELL_KNOWN = {"pkg:npm/lodash@4.17.21": "MIT", "pkg:pypi/requests@2.31.0": "Apache-2.0"}
UNEVALUABLE = ["not-a-purl", "pkg:npm/lodash"]


@unittest.skipUnless(REPO, "set GH_LICENSE_CHECK_LIVE_REPO to run live tests")
class LiveApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.transport = GhApiTransport(hostname=HOSTNAME)
        cls.purls = [*WELL_KNOWN, *UNEVALUABLE, *EXPECT]
        cls.results = cls.transport.check(REPO, cls.purls)["purls"]

    def test_every_submitted_purl_is_answered(self):
        self.assertEqual(set(self.results), set(self.purls))

    def test_values_are_in_known_enums(self):
        for purl, result in self.results.items():
            with self.subTest(purl=purl):
                self.assertIn(result["status"], m.STATUSES)
                self.assertIn(result["reason"], m.REASONS)

    def test_license_data_for_well_known_packages(self):
        for purl, license_ in WELL_KNOWN.items():
            with self.subTest(purl=purl):
                self.assertEqual(self.results[purl]["license"], license_)

    def test_unevaluable_purls_are_unknown(self):
        for purl in UNEVALUABLE:
            with self.subTest(purl=purl):
                self.assertEqual(
                    self.results[purl],
                    {"status": m.STATUS_UNKNOWN, "license": None, "reason": m.REASON_UNKNOWN},
                )

    def test_expected_verdicts(self):
        if not EXPECT:
            self.skipTest("set GH_LICENSE_CHECK_LIVE_EXPECT to pin verdicts")
        for purl, status in EXPECT.items():
            with self.subTest(purl=purl):
                self.assertEqual(self.results[purl]["status"], status)

    def test_empty_request_is_rejected(self):
        with self.assertRaises(ApiError) as ctx:
            self.transport.check(REPO, [])
        self.assertEqual(ctx.exception.status, 422)

    def test_inaccessible_repo_is_not_found(self):
        owner = REPO.split("/")[0]
        with self.assertRaises(ApiError) as ctx:
            self.transport.check(f"{owner}/gh-license-check-no-such-repo", list(WELL_KNOWN))
        self.assertEqual(ctx.exception.status, 404)


if __name__ == "__main__":
    unittest.main()
