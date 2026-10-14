"""Tests for the gh api transport, using a fake runner in place of `gh`.

Error payloads mirror what `gh api` actually prints for HTTP errors: the JSON
error body on stdout and `gh: <message> (HTTP <status>)` on stderr.
"""

import json
import subprocess
import unittest

from license_check.transports import ApiError, GhApiTransport, current_repo

DOCS = "https://docs.github.com/rest/dependency-graph/license-compliance#check-license-compliance-for-packages"


class FakeRunner:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.result = (returncode, stdout, stderr)
        self.calls = []

    def __call__(self, cmd, **kwargs):
        self.calls.append((cmd, kwargs))
        code, out, err = self.result
        return subprocess.CompletedProcess(cmd, code, out, err)


def _error(status, message):
    body = json.dumps({"message": message, "documentation_url": DOCS, "status": str(status)})
    return FakeRunner(1, body, f"gh: {message} (HTTP {status})\n")


class GhApiTransportRequestTests(unittest.TestCase):
    def test_posts_purls_to_repo_endpoint(self):
        runner = FakeRunner(0, json.dumps({"purls": {}}))
        GhApiTransport(runner=runner).check("octo/repo", ["pkg:npm/a@1.0.0", "pkg:npm/b@2.0.0"])

        cmd, kwargs = runner.calls[0]
        self.assertEqual(
            cmd,
            ["gh", "api", "--method", "POST",
             "repos/octo/repo/license-compliance/package-checks", "--input", "-"],
        )
        self.assertEqual(json.loads(kwargs["input"]), {"purls": ["pkg:npm/a@1.0.0", "pkg:npm/b@2.0.0"]})

    def test_hostname_is_passed_to_gh(self):
        runner = FakeRunner(0, json.dumps({"purls": {}}))
        GhApiTransport(hostname="ghe.example.com", runner=runner).check("octo/repo", ["pkg:npm/a@1.0.0"])
        cmd, _ = runner.calls[0]
        self.assertEqual(cmd[-2:], ["--hostname", "ghe.example.com"])

    def test_returns_parsed_body(self):
        body = {"purls": {"pkg:npm/a@1.0.0": {"status": "allowed", "license": "MIT", "reason": "allowed_license"}}}
        runner = FakeRunner(0, json.dumps(body))
        self.assertEqual(GhApiTransport(runner=runner).check("octo/repo", ["pkg:npm/a@1.0.0"]), body)

    def test_rejects_malformed_repo_without_calling_gh(self):
        runner = FakeRunner()
        for bad in ["repo", "octo/", "/repo", "a/b/c"]:
            with self.assertRaises(ValueError):
                GhApiTransport(runner=runner).check(bad, ["pkg:npm/a@1.0.0"])
        self.assertEqual(runner.calls, [])


class GhApiTransportErrorTests(unittest.TestCase):
    def _raise(self, runner):
        with self.assertRaises(ApiError) as ctx:
            GhApiTransport(runner=runner).check("octo/repo", ["pkg:npm/a@1.0.0"])
        return ctx.exception

    def test_404_explains_access(self):
        err = self._raise(_error(404, "Not Found"))
        self.assertEqual(err.status, 404)
        self.assertIn("no license policy", str(err))

    def test_422_surfaces_server_message(self):
        err = self._raise(_error(422, "Invalid request.\n\nInvalid property /purls: 1 item required; only 0 were supplied."))
        self.assertEqual(err.status, 422)
        self.assertIn("1 item required", str(err))

    def test_503_suggests_smaller_batches(self):
        err = self._raise(_error(503, "Unable to check license compliance for the supplied packages. Please try again later."))
        self.assertEqual(err.status, 503)
        self.assertIn("fewer PURLs", str(err))

    def test_non_http_failure_uses_stderr(self):
        err = self._raise(FakeRunner(4, "", "gh: To get started with GitHub CLI, please run:  gh auth login\n"))
        self.assertIsNone(err.status)
        self.assertIn("gh auth login", str(err))


class CurrentRepoTests(unittest.TestCase):
    def test_reads_name_with_owner(self):
        runner = FakeRunner(0, "octo/repo\n")
        self.assertEqual(current_repo(runner=runner), "octo/repo")
        self.assertEqual(runner.calls[0][0][:3], ["gh", "repo", "view"])

    def test_outside_a_repo_asks_for_repo_flag(self):
        runner = FakeRunner(1, "", "failed to run git: fatal: not a git repository\n")
        with self.assertRaises(ValueError) as ctx:
            current_repo(runner=runner)
        self.assertIn("--repo", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
