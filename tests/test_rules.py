"""Tests for the rules engine."""

from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


class TestRules(unittest.TestCase):
    def setUp(self) -> None:
        # Isolate paths for each test by setting env vars before import.
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        os.environ["OPENCODE_ROUTER_RULES"] = str(Path(self.tmp.name) / "rules.json")
        # Re-import to pick up env-var paths.
        import importlib

        from opencode_router import paths, rules

        importlib.reload(paths)
        importlib.reload(rules)
        self.rules = rules

    def test_default_rules_match_security_reviewer_to_pro(self) -> None:
        ruleset = self.rules.load()
        bucket = ruleset.pick(
            "security-reviewer", "Reviews code for security vulnerabilities"
        )
        self.assertEqual(bucket, "pro")

    def test_default_rules_match_typescript_reviewer_to_flash(self) -> None:
        ruleset = self.rules.load()
        bucket = ruleset.pick("typescript-reviewer", "Reviews TypeScript code")
        self.assertEqual(bucket, "flash")

    def test_default_rules_match_backend_architect_to_coding(self) -> None:
        ruleset = self.rules.load()
        bucket = ruleset.pick(
            "backend-architect", "Designs scalable backend systems"
        )
        self.assertEqual(bucket, "coding")

    def test_default_falls_through_to_pro(self) -> None:
        ruleset = self.rules.load()
        bucket = ruleset.pick("totally-novel-thing", "does novel work")
        self.assertEqual(bucket, "pro")

    def test_user_rules_override_defaults(self) -> None:
        rules_path = Path(os.environ["OPENCODE_ROUTER_RULES"])
        rules_path.write_text(
            json.dumps(
                {
                    "rules": [["my-special-agent", "coding"]],
                    "default_bucket": "flash",
                }
            ),
            encoding="utf-8",
        )
        ruleset = self.rules.load()
        self.assertEqual(ruleset.pick("my-special-agent", ""), "coding")
        self.assertEqual(ruleset.pick("anything-else", ""), "flash")

    def test_extend_mode_prepends_user_rules_to_defaults(self) -> None:
        rules_path = Path(os.environ["OPENCODE_ROUTER_RULES"])
        rules_path.write_text(
            json.dumps(
                {
                    "mode": "extend",
                    "rules": [["frontend-developer", "visual"]],
                }
            ),
            encoding="utf-8",
        )
        ruleset = self.rules.load()
        # User override wins over the default `("frontend", "coding")`
        self.assertEqual(
            ruleset.pick("frontend-developer", "Builds React UIs"),
            "visual",
        )
        # Defaults still in effect for unrelated agents
        self.assertEqual(
            ruleset.pick("typescript-reviewer", "Reviews TypeScript"),
            "flash",
        )
        self.assertEqual(
            ruleset.pick("backend-architect", "Designs APIs"),
            "coding",
        )


if __name__ == "__main__":
    unittest.main()
