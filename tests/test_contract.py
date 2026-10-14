"""Contract tests against a recorded live API response.

tests/data/live_response.json was captured from the real endpoint. The
verdicts depend on the policy of the repository it was recorded against, so
these tests only rely on that file's shape and conventions, and check that
the CLI and the mock both follow them.
"""

import contextlib
import io
import json
import unittest
from pathlib import Path
from unittest import mock

from license_check import cli
from license_check import models as m
from license_check.transports import MockTransport

ROOT = Path(__file__).resolve().parent.parent
LIVE = json.loads((ROOT / "tests" / "data" / "live_response.json").read_text())


def _run(argv, response=LIVE):
    """Run the CLI with the API transport stubbed to return `response`."""
    seen = {}

    def fake_check(self, repo, purls):
        seen["repo"], seen["purls"] = repo, purls
        return response

    out, err = io.StringIO(), io.StringIO()
    with mock.patch.object(cli.GhApiTransport, "check", fake_check), \
            contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(argv)
    return code, out.getvalue(), err.getvalue(), seen


class RecordedResponseShapeTests(unittest.TestCase):
    def test_values_are_in_known_enums(self):
        for purl, result in LIVE["purls"].items():
            with self.subTest(purl=purl):
                self.assertEqual(set(result), {"status", "license", "reason"})
                self.assertIn(result["status"], m.STATUSES)
                self.assertIn(result["reason"], m.REASONS)

    def test_unknown_has_null_license_and_unknown_reason(self):
        unknowns = [r for r in LIVE["purls"].values() if r["status"] == m.STATUS_UNKNOWN]
        self.assertTrue(unknowns)
        for r in unknowns:
            self.assertIsNone(r["license"])
            self.assertEqual(r["reason"], m.REASON_UNKNOWN)


class CliAgainstRecordedResponseTests(unittest.TestCase):
    def test_json_passes_response_through(self):
        purls = list(LIVE["purls"])
        code, out, err, seen = _run(["--repo", "octo/repo", "--json", *purls])
        self.assertEqual(json.loads(out), LIVE)
        self.assertEqual(seen["purls"], purls)
        self.assertEqual(err, "")
        self.assertEqual(code, 1)

    def test_table_shows_every_purl(self):
        purls = list(LIVE["purls"])
        _, out, _, _ = _run(["--repo", "octo/repo", *purls])
        for purl in purls:
            self.assertIn(purl, out)

    def test_exit_zero_when_all_allowed(self):
        allowed = [p for p, r in LIVE["purls"].items() if r["status"] == m.STATUS_ALLOWED]
        code, *_ = _run(["--repo", "octo/repo", *allowed])
        self.assertEqual(code, 0)

    def test_fail_on_denied_ignores_unknown(self):
        unknown = [p for p, r in LIVE["purls"].items() if r["status"] == m.STATUS_UNKNOWN]
        self.assertEqual(_run(["--repo", "octo/repo", *unknown])[0], 1)
        self.assertEqual(_run(["--repo", "octo/repo", "--fail-on", "denied", *unknown])[0], 0)

    def test_purl_missing_from_response_fails_safe(self):
        code, *_ = _run(["--repo", "octo/repo", "pkg:npm/a@1.0.0"], response={"purls": {}})
        self.assertEqual(code, 1)

    def test_repo_defaults_to_current_directory(self):
        with mock.patch.object(cli, "current_repo", return_value="octo/here"):
            _, _, _, seen = _run(["pkg:npm/lodash@4.17.21"])
        self.assertEqual(seen["repo"], "octo/here")

    def test_missing_repo_context_is_a_usage_error(self):
        with mock.patch.object(cli, "current_repo", side_effect=ValueError("pass --repo OWNER/REPO")):
            code, _, err, _ = _run(["pkg:npm/lodash@4.17.21"])
        self.assertEqual(code, 2)
        self.assertIn("--repo", err)


class MockMatchesLiveConventionsTests(unittest.TestCase):
    """The mock should produce the same shapes the live API does."""

    def setUp(self):
        self.mock = MockTransport(ROOT / "fixtures")

    def _mock(self, purl):
        return self.mock.check("octo/repo", [purl])["purls"][purl]

    def test_unparseable_and_versionless_purls(self):
        for purl in ["not-a-purl", "pkg:npm/lodash"]:
            with self.subTest(purl=purl):
                self.assertEqual(self._mock(purl), LIVE["purls"][purl])

    def test_package_without_license_data_is_denied_with_null_license(self):
        self.assertEqual(
            self._mock("pkg:npm/does-not-exist-zzz@0.0.1"),
            LIVE["purls"]["pkg:npm/does-not-exist-zzz@0.0.1"],
        )


if __name__ == "__main__":
    unittest.main()
