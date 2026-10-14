import contextlib
import io
import json
import unittest
from pathlib import Path

from license_check.cli import main

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"


def _frontmatter(text: str) -> dict:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fields = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    return fields


class SkillTests(unittest.TestCase):
    def test_skill_frontmatter_matches_directory(self):
        skill_dirs = [p for p in SKILLS.iterdir() if p.is_dir()]
        self.assertTrue(skill_dirs, "expected at least one skill")
        for skill_dir in skill_dirs:
            fm = _frontmatter((skill_dir / "SKILL.md").read_text(encoding="utf-8"))
            self.assertEqual(fm.get("name"), skill_dir.name)
            self.assertTrue(fm.get("description"))


class CliOutputTests(unittest.TestCase):
    def test_mock_json_stdout_is_clean_and_notice_on_stderr(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(["--mock", "--json", "pkg:npm/lodash@4.17.21"])
        self.assertEqual(code, 0)
        body = json.loads(out.getvalue())
        self.assertEqual(body["purls"]["pkg:npm/lodash@4.17.21"]["status"], "allowed")
        self.assertIn("--mock", err.getvalue())


if __name__ == "__main__":
    unittest.main()
