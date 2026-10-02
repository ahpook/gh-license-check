import unittest
from pathlib import Path

from license_check import models as m
from license_check.transports import MockTransport

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


class MockTransportTests(unittest.TestCase):
    def setUp(self):
        self.t = MockTransport(FIXTURES)

    def _result(self, purl):
        return self.t.check("OWNER/REPO", [purl])["purls"][purl]

    def test_allowed_license(self):
        r = self._result("pkg:npm/lodash@4.17.21")
        self.assertEqual(r["status"], m.STATUS_ALLOWED)
        self.assertEqual(r["reason"], m.REASON_ALLOWED_LICENSE)
        self.assertEqual(r["license"], "MIT")

    def test_denied_license(self):
        r = self._result("pkg:pypi/requests@2.31.0")
        self.assertEqual(r["status"], m.STATUS_DENIED)
        self.assertEqual(r["reason"], m.REASON_DENIED_LICENSE)

    def test_allowed_package_exception(self):
        r = self._result("pkg:pypi/exemption@2.31.0")
        self.assertEqual(r["status"], m.STATUS_ALLOWED)
        self.assertEqual(r["reason"], m.REASON_ALLOWED_PACKAGE)

    def test_denied_package_exception(self):
        r = self._result("pkg:npm/blocked-pkg@1.0.0")
        self.assertEqual(r["status"], m.STATUS_DENIED)
        self.assertEqual(r["reason"], m.REASON_DENIED_PACKAGE)

    def test_disjunction_allowed(self):
        r = self._result("pkg:npm/dual-licensed-pkg@1.0.0")
        self.assertEqual(r["status"], m.STATUS_ALLOWED)

    def test_conjunction_denied(self):
        r = self._result("pkg:npm/compound-pkg@2.0.0")
        self.assertEqual(r["status"], m.STATUS_DENIED)

    def test_unknown_when_no_license_data(self):
        r = self._result("pkg:npm/does-not-exist@9.9.9")
        self.assertEqual(r["status"], m.STATUS_UNKNOWN)
        self.assertIsNone(r["license"])
        self.assertIsNone(r["reason"])

    def test_unknown_when_malformed_purl(self):
        r = self._result("not-a-purl")
        self.assertEqual(r["status"], m.STATUS_UNKNOWN)


if __name__ == "__main__":
    unittest.main()
