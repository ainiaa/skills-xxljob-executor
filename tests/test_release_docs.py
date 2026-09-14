import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class ReleaseDocsTest(unittest.TestCase):
    def test_public_documentation_uses_only_generic_examples(self):
        forbidden_values = ("10.93" + ".1.143", "syncAegis" + "TradeFlowHandler", "acct_" + "x", "/Users/" + "liuwenyuan")
        public_files = (ROOT / "README.md", ROOT / "SKILL.md", ROOT / "scripts" / "run_xxl_job.py")

        for public_file in public_files:
            content = public_file.read_text()
            for forbidden_value in forbidden_values:
                self.assertNotIn(forbidden_value, content, public_file)

    def test_coverage_gate_is_90_percent_and_tracks_subprocesses(self):
        coverage_config = (ROOT / ".coveragerc").read_text()

        self.assertIn("source = scripts", coverage_config)
        self.assertIn("patch = subprocess", coverage_config)
        self.assertIn("fail_under = 90", coverage_config)

    def test_readme_version_and_changelog_are_consistent(self):
        self.assertTrue((ROOT / "VERSION").is_file())
        self.assertTrue((ROOT / "CHANGELOG.md").is_file())
        version = (ROOT / "VERSION").read_text().strip()
        readme = (ROOT / "README.md").read_text()
        changelog = (ROOT / "CHANGELOG.md").read_text()

        self.assertEqual("0.1.0", version)
        self.assertIn("当前发布版本：[0.1.0](VERSION)", readme)
        self.assertIn("[变更日志](CHANGELOG.md)", readme)
        self.assertIn("## 快速开始", readme)
        self.assertIn("scripts/run_xxl_job.py", readme)
        self.assertIn("--access-token-env", readme)
        self.assertIn("--job-id", readme)
        self.assertIn("--allow-insecure-http-token", readme)
        self.assertNotIn("## 验证", readme)
        self.assertIn("## 使用 Skill", readme)
        self.assertIn("Keep a Changelog", changelog)
        self.assertIn("## [Unreleased]", changelog)
        self.assertIn("## [0.1.0] - 2026-09-14", changelog)
        self.assertEqual(1, changelog.count("## [0.1.0]"))
        self.assertIn("90%", changelog)


if __name__ == "__main__":
    unittest.main()
