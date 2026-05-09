"""Tests for profile management."""

from __future__ import annotations

import importlib
import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


SAMPLE = {
    "active": "alpha",
    "profiles": {
        "alpha": {
            "description": "alpha profile",
            "buckets": {
                "pro": "provider/pro-model",
                "flash": "provider/flash-model",
            },
        },
        "beta": {
            "description": "beta profile",
            "buckets": {
                "pro": "other/pro",
                "flash": "other/flash",
                "coding": "other/coding",
            },
        },
    },
}


class TestProfile(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        os.environ["OPENCODE_ROUTER_PROFILE"] = str(
            Path(self.tmp.name) / "profile.json"
        )
        from opencode_router import paths, profile

        importlib.reload(paths)
        importlib.reload(profile)
        self.profile = profile
        Path(os.environ["OPENCODE_ROUTER_PROFILE"]).write_text(
            json.dumps(SAMPLE), encoding="utf-8"
        )

    def test_active_returns_active_name(self) -> None:
        self.assertEqual(self.profile.active_name(), "alpha")

    def test_get_active_returns_full_profile(self) -> None:
        p = self.profile.get_active()
        self.assertEqual(p.name, "alpha")
        self.assertEqual(p.buckets["pro"], "provider/pro-model")

    def test_missing_buckets_fall_back_to_pro(self) -> None:
        p = self.profile.get_active()
        # alpha has only pro+flash defined. coding/visual/etc fall back to pro.
        self.assertEqual(p.buckets["coding"], "provider/pro-model")
        self.assertEqual(p.buckets["visual"], "provider/pro-model")

    def test_set_active_changes_active_field(self) -> None:
        self.profile.set_active("beta")
        self.assertEqual(self.profile.active_name(), "beta")

    def test_set_active_rejects_unknown(self) -> None:
        with self.assertRaises(SystemExit):
            self.profile.set_active("nonexistent")


if __name__ == "__main__":
    unittest.main()
