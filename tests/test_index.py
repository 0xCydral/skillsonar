import json

import pytest

from skillsonar.errors import SkillIndexError
from skillsonar.index import keyword_rank, load_index, save_index, scan


def write_skill(root, rel, body):
    folder = root / rel
    folder.mkdir(parents=True)
    (folder / "SKILL.md").write_text(body, encoding="utf-8")
    return folder


def test_scan_finds_every_fixture(skills_dir):
    entries = scan([skills_dir])
    names = {e["name"] for e in entries}
    assert len(entries) == 21
    assert {"kubernetes-pod-debugging", "git-rebase-cleanup", "sql-query-tuning"} <= names


def test_block_scalar_fixtures_keep_their_description(skills_dir):
    by_name = {e["name"]: e for e in scan([skills_dir])}
    assert by_name["git-rebase-cleanup"]["desc"].startswith("Rewrite messy branch history")
    assert "execution plan" in by_name["sql-query-tuning"]["desc"]
    assert by_name["git-rebase-cleanup"]["desc"] != "|"


def test_scan_is_recursive_and_skips_hidden_dirs(tmp_path):
    write_skill(tmp_path, "group/deep/one", "---\nname: one\ndescription: Alpha skill.\n---\n")
    write_skill(tmp_path, ".archive/old", "---\nname: old\ndescription: Retired skill.\n---\n")
    assert [e["name"] for e in scan([tmp_path])] == ["one"]


def test_name_falls_back_to_folder(tmp_path):
    write_skill(tmp_path, "my-folder", "# Heading only\nSome words about kubernetes pods.\n")
    assert scan([tmp_path])[0]["name"] == "my-folder"


def test_same_folder_through_two_roots_is_indexed_once(tmp_path):
    write_skill(tmp_path, "a/one", "---\nname: one\ndescription: Alpha skill.\n---\n")
    assert len(scan([tmp_path, tmp_path / "a"])) == 1


def test_missing_root_is_ignored(tmp_path):
    assert scan([tmp_path / "nope"]) == []


def test_save_and_load_round_trip(tmp_path, skills_dir):
    entries = scan([skills_dir])
    save_index(tmp_path, entries)
    assert load_index(tmp_path)["entries"] == entries


def test_missing_index_names_the_fix(tmp_path):
    with pytest.raises(SkillIndexError, match="skillsonar build"):
        load_index(tmp_path)


def test_corrupt_index_is_a_clean_error(tmp_path):
    (tmp_path / "index.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(SkillIndexError, match="rebuild"):
        load_index(tmp_path)


def test_source_label_is_relative_to_cwd(tmp_path, skills_dir, monkeypatch):
    monkeypatch.chdir(skills_dir.parent.parent.parent)
    save_index(tmp_path, scan([skills_dir]))
    sources = {e["source"] for e in json.loads((tmp_path / "index.json").read_text())["entries"]}
    assert sources == {"tests/fixtures/skills"}


def test_keyword_ranking_puts_the_right_skill_first(skills_dir):
    entries = scan([skills_dir])
    top = keyword_rank(entries, "my pod keeps restarting")[0][0]
    assert top["name"] == "kubernetes-pod-debugging"


def test_name_match_adds_a_bonus(tmp_path):
    write_skill(tmp_path, "a", "---\nname: terraform\ndescription: Infrastructure code.\n---\n")
    write_skill(tmp_path, "b", "---\nname: other\ndescription: Terraform infrastructure code.\n---\n")
    ranked = keyword_rank(scan([tmp_path]), "terraform infrastructure")
    assert [e["name"] for e, _ in ranked] == ["terraform", "other"]


def test_query_with_no_overlap_returns_nothing(skills_dir):
    assert keyword_rank(scan([skills_dir]), "zzzz qqqq") == []
