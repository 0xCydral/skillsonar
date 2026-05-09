"""Tests for agent file parsing."""

from __future__ import annotations

import textwrap
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from opencode_router import agents


class TestFrontmatter(unittest.TestCase):
    def test_extracts_simple_frontmatter(self) -> None:
        text = textwrap.dedent(
            """\
            ---
            name: Foo
            description: Does foo things
            mode: subagent
            ---
            body
            """
        )
        fm = agents.parse_frontmatter(text)
        self.assertEqual(fm["name"], "Foo")
        self.assertEqual(fm["description"], "Does foo things")
        self.assertEqual(fm["mode"], "subagent")

    def test_strips_quotes(self) -> None:
        text = '---\ndescription: "Quoted desc"\n---\nbody\n'
        fm = agents.parse_frontmatter(text)
        self.assertEqual(fm["description"], "Quoted desc")

    def test_no_frontmatter_returns_empty(self) -> None:
        self.assertEqual(agents.parse_frontmatter("no frontmatter\n"), {})


class TestParseAgentFile(unittest.TestCase):
    def test_uses_filename_for_name(self) -> None:
        with TemporaryDirectory() as d:
            path = Path(d) / "code-reviewer.md"
            path.write_text(
                "---\ndescription: Reviews code\nmode: subagent\n---\n\nbody\n",
                encoding="utf-8",
            )
            agent = agents.parse_agent_file(path)
            self.assertEqual(agent.name, "code-reviewer")
            self.assertEqual(agent.description, "Reviews code")
            self.assertEqual(agent.mode, "subagent")

    def test_default_mode_is_subagent(self) -> None:
        with TemporaryDirectory() as d:
            path = Path(d) / "minimal.md"
            path.write_text(
                "---\ndescription: x\n---\n\n",
                encoding="utf-8",
            )
            agent = agents.parse_agent_file(path)
            self.assertEqual(agent.mode, "subagent")

    def test_default_description_when_missing(self) -> None:
        with TemporaryDirectory() as d:
            path = Path(d) / "my-agent.md"
            path.write_text("---\n---\n\nbody\n", encoding="utf-8")
            agent = agents.parse_agent_file(path)
            self.assertIn("My Agent", agent.description)


class TestEmbedText(unittest.TestCase):
    def test_combines_name_and_description(self) -> None:
        agent = agents.Agent(
            name="db-optimizer",
            description="Optimizes SQL queries",
            mode="subagent",
            raw_frontmatter={},
        )
        text = agents.embed_text_for(agent)
        self.assertIn("db optimizer", text)
        self.assertIn("Optimizes SQL queries", text)


if __name__ == "__main__":
    unittest.main()
