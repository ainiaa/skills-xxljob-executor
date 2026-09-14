import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class ReleaseDocsTest(unittest.TestCase):
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
        self.assertIn("python3 -m coverage run", readme)
        self.assertIn("Keep a Changelog", changelog)
        self.assertIn("## [Unreleased]", changelog)
        self.assertIn("## [0.1.0] - 2026-09-14", changelog)
        self.assertEqual(1, changelog.count("## [0.1.0]"))
        self.assertIn("90%", changelog)


if __name__ == "__main__":
    unittest.main()
