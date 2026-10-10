import json

from skillsonar import __version__
from skillsonar.cli import main

from .conftest import FakeReranker


def test_build_reports_count(tmp_path, skills_dir, capsys):
    assert main(["build", "--path", str(skills_dir), "--index", str(tmp_path)]) == 0
    assert "indexed 21 skills" in capsys.readouterr().out
    assert (tmp_path / "index.json").is_file()


def test_build_with_no_skills_is_an_error(tmp_path, capsys):
    empty = tmp_path / "empty"
    empty.mkdir()
    assert main(["build", "--path", str(empty), "--index", str(tmp_path / "idx")]) == 1
    assert "no skills found" in capsys.readouterr().err


def test_env_paths_replace_defaults(tmp_path, skills_dir, monkeypatch, capsys):
    monkeypatch.setenv("SKILLSONAR_PATHS", str(skills_dir))
    assert main(["build", "--index", str(tmp_path)]) == 0
    assert "indexed 21 skills" in capsys.readouterr().out


def test_search_text_output(index_dir, capsys):
    assert main(["search", "my pod keeps restarting", "--index", str(index_dir)]) == 0
    out = capsys.readouterr().out
    assert out.startswith("1. kubernetes-pod-debugging")
    assert "kubectl" in out


def test_search_json_output(index_dir, capsys):
    assert main(["search", "pod restart commit", "--json", "--top", "2", "--index", str(index_dir)]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert len(rows) == 2
    assert rows[0]["name"] == "kubernetes-pod-debugging"
    assert set(rows[0]) == {"name", "score", "source", "path", "desc"}


def test_search_with_path_filter(index_dir, skills_dir, tmp_path, capsys):
    other = tmp_path / "other"
    other.mkdir()
    assert main(["search", "pod restart", "--path", str(other), "--index", str(index_dir)]) == 0
    assert capsys.readouterr().out.strip() == "no matches"
    assert main(["search", "pod restart", "--path", str(skills_dir), "--index", str(index_dir)]) == 0
    assert "kubernetes-pod-debugging" in capsys.readouterr().out


def test_duplicate_skills_show_once_with_their_other_folders(tmp_path, capsys):
    for root in ("first", "second"):
        folder = tmp_path / root / "one"
        folder.mkdir(parents=True)
        (folder / "SKILL.md").write_text("---\nname: one\ndescription: Alpha widget.\n---\n", encoding="utf-8")
    index = tmp_path / "idx"
    paths = ["--path", str(tmp_path / "first"), "--path", str(tmp_path / "second")]
    assert main(["build", *paths, "--index", str(index)]) == 0
    assert main(["search", "alpha widget", "--index", str(index)]) == 0
    out = capsys.readouterr().out
    assert out.count("1. one") == 1
    assert "2. " not in out
    assert "also in: 1 other folder(s)" in out
    assert main(["search", "alpha widget", "--json", "--index", str(index)]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert len(rows) == 1
    assert len(rows[0]["also"]) == 1
    assert main(["stats", "--index", str(index)]) == 0
    assert "duplicates collapsed: 1" in capsys.readouterr().out
    # --path matches a collapsed skill through any of its copies, not only the kept one.
    assert main(["search", "alpha widget", "--path", str(tmp_path / "second"), "--index", str(index)]) == 0
    assert "1. one" in capsys.readouterr().out


def test_embeddings_follow_the_collapsed_entries(tmp_path, fake_ollama, capsys):
    for root in ("first", "second"):
        folder = tmp_path / root / "one"
        folder.mkdir(parents=True)
        (folder / "SKILL.md").write_text("---\nname: one\ndescription: Alpha widget.\n---\n", encoding="utf-8")
    index = tmp_path / "idx"
    paths = ["--path", str(tmp_path / "first"), "--path", str(tmp_path / "second")]
    assert main(["build", *paths, "--index", str(index), "--embed"]) == 0
    assert "embedded 1 skills" in capsys.readouterr().out
    assert main(["search", "alpha widget", "--hybrid", "--index", str(index)]) == 0
    assert capsys.readouterr().out.startswith("1. one")


def test_missing_index_is_a_clean_error(tmp_path, capsys):
    assert main(["search", "anything", "--index", str(tmp_path / "none")]) == 1
    err = capsys.readouterr().err
    assert err.startswith("skillsonar: no index at")
    assert "skillsonar build" in err


def test_stats(index_dir, capsys):
    assert main(["stats", "--index", str(index_dir)]) == 0
    out = capsys.readouterr().out
    assert "skills: 21" in out
    assert "embeddings: none" in out


def test_build_embed_then_semantic_and_hybrid_search(index_dir, skills_dir, fake_ollama, capsys):
    assert main(["build", "--path", str(skills_dir), "--index", str(index_dir), "--embed"]) == 0
    assert "embedded 21 skills with fake-embed" in capsys.readouterr().out
    for flag in ("--semantic", "--hybrid"):
        assert main(["search", "kubernetes pod crash restart", flag, "--index", str(index_dir)]) == 0
        assert capsys.readouterr().out.startswith("1. kubernetes-pod-debugging")
    assert main(["stats", "--index", str(index_dir)]) == 0
    assert "embeddings: fake-embed, 21 vectors" in capsys.readouterr().out


def test_semantic_search_without_embeddings_is_a_clean_error(index_dir, fake_ollama, capsys):
    assert main(["search", "pod", "--semantic", "--index", str(index_dir)]) == 1
    assert "build --embed" in capsys.readouterr().err


def test_unreachable_ollama_is_a_clean_error(index_dir, skills_dir, monkeypatch, capsys):
    from skillsonar.errors import OllamaError

    class Down:
        model = "bge-m3"

        def embed(self, texts):
            raise OllamaError("embeddings failed at http://127.0.0.1:1 (refused); is Ollama running?")

    monkeypatch.setattr("skillsonar.cli.OllamaClient", type("C", (), {"from_env": staticmethod(Down)}))
    assert main(["build", "--path", str(skills_dir), "--index", str(index_dir), "--embed"]) == 1
    assert "is Ollama running" in capsys.readouterr().err


def test_rerank_flag_uses_the_client(index_dir, monkeypatch, capsys):
    fake = FakeReranker("Terraform")
    monkeypatch.setattr("skillsonar.cli.RerankClient", type("R", (), {"from_env": staticmethod(lambda: fake)}))
    assert main(["search", "infrastructure code state", "--rerank", "--index", str(index_dir)]) == 0
    assert capsys.readouterr().out.startswith("1. terraform-modules")


def test_rerank_without_configuration_is_a_clean_error(index_dir, monkeypatch, capsys):
    monkeypatch.delenv("SKILLSONAR_RERANK_BASE_URL", raising=False)
    monkeypatch.delenv("SKILLSONAR_RERANK_MODEL", raising=False)
    assert main(["search", "pod", "--rerank", "--index", str(index_dir)]) == 1
    assert "SKILLSONAR_RERANK_BASE_URL" in capsys.readouterr().err


def test_eval_prints_recall(index_dir, queries_file, capsys):
    assert main(["eval", str(queries_file), "--k", "5", "--index", str(index_dir)]) == 0
    out = capsys.readouterr().out
    assert "mode: keyword" in out
    assert "recall@5:" in out


def test_version(capsys):
    try:
        main(["--version"])
    except SystemExit as exit_:
        assert exit_.code == 0
    assert __version__ in capsys.readouterr().out
