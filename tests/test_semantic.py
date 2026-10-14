import pytest

from skillsonar.errors import OllamaError, RerankError, SkillIndexError
from skillsonar.evaluate import evaluate, load_queries
from skillsonar.index import scan
from skillsonar.ollama import OllamaClient
from skillsonar.rerank import RerankClient, parse_ranking
from skillsonar.search import Searcher, rrf
from skillsonar.semantic import (
    build_embeddings,
    document_for,
    load_embeddings,
    save_embeddings,
    semantic_rank,
    unit,
)

from .conftest import FakeOllama, FakeReranker


def entry(name):
    return {"name": name, "path": f"/x/{name}", "desc": ""}


def test_rrf_rewards_agreement():
    a, b, c = entry("a"), entry("b"), entry("c")
    fused = rrf([[a, b, c], [b, c]])
    assert [e["name"] for e, _ in fused] == ["b", "c", "a"]


def test_rrf_score_matches_the_formula():
    a = entry("a")
    (_, score), = rrf([[a], [a]], k=60)
    assert score == pytest.approx(2 / 61)


def test_unit_vector_has_length_one():
    assert sum(x * x for x in unit([3.0, 4.0])) == pytest.approx(1.0)
    assert unit([0.0, 0.0]) == [0.0, 0.0]


def test_semantic_rank_orders_by_cosine():
    a, b = entry("a"), entry("b")
    vectors = {"/x/a": unit([1.0, 0.0]), "/x/b": unit([0.0, 1.0])}
    ranked = semantic_rank([a, b], vectors, [0.1, 2.0])
    assert [e["name"] for e, _ in ranked] == ["b", "a"]


def test_document_for_includes_headings_and_drops_frontmatter(skills_dir):
    e = next(x for x in scan([skills_dir]) if x["name"] == "kubernetes-pod-debugging")
    doc = document_for(e)
    assert "Crashes and restarts" in doc
    assert "name: kubernetes" not in doc


def test_embeddings_round_trip_and_staleness(tmp_path, skills_dir):
    entries = scan([skills_dir])
    save_embeddings(tmp_path, build_embeddings(entries, FakeOllama()))
    assert set(load_embeddings(tmp_path, entries)) == {e["path"] for e in entries}
    with pytest.raises(SkillIndexError, match="out of date"):
        load_embeddings(tmp_path, [*entries, entry("new")])


def test_missing_embeddings_name_the_fix(tmp_path):
    with pytest.raises(SkillIndexError, match="build --embed"):
        load_embeddings(tmp_path, [])


@pytest.fixture
def searcher(tmp_path, skills_dir):
    entries = scan([skills_dir])
    fake = FakeOllama()
    save_embeddings(tmp_path, build_embeddings(entries, fake))
    return Searcher(entries, tmp_path, fake)


def test_semantic_and_hybrid_modes_find_the_skill(searcher):
    query = "kubernetes pod crash restart logs"
    for mode in ("semantic", "hybrid"):
        assert searcher.rank(query, mode)[0][0]["name"] == "kubernetes-pod-debugging"


def test_restrict_limits_results(tmp_path, skills_dir):
    entries = scan([skills_dir])
    only = Searcher(entries, tmp_path, restrict=lambda e: e["name"] == "regex-builder")
    assert [e["name"] for e, _ in only.rank("regex pattern backtracking")] == ["regex-builder"]


def test_rerank_reorders_the_shortlist_and_sends_name_and_description(searcher):
    reranker = FakeReranker("Terraform")
    results = searcher.search("infrastructure code state", "keyword", 3, reranker)
    assert [e["name"] for e, _ in results] == ["terraform-modules"]
    assert any(line.startswith("terraform-modules: Structure Terraform") for line in reranker.seen[0])


def test_rerank_falls_back_to_first_stage_when_unparseable(searcher):
    results = searcher.search("pod restart", "keyword", 2, FakeReranker("no such word"))
    assert results[0][0]["name"] == "kubernetes-pod-debugging"


def test_eval_reports_recall_and_misses(skills_dir, tmp_path):
    searcher = Searcher(scan([skills_dir]), tmp_path)
    queries = [
        ("pod keeps restarting", ["kubernetes-pod-debugging"]),
        ("zzzz qqqq", ["regex-builder"]),
        ("rebase squash", ["git-rebase-cleanup", "regex-builder"]),
    ]
    report = evaluate(searcher, queries, 5, "keyword")
    assert report.queries == 3
    assert report.recall == pytest.approx((1 + 0 + 0.5) / 3)
    assert report.first_hits == 2
    assert [m.query for m in report.misses] == ["zzzz qqqq", "rebase squash"]


def test_eval_rejects_expected_names_not_in_the_index(skills_dir, tmp_path):
    searcher = Searcher(scan([skills_dir]), tmp_path)
    with pytest.raises(SkillIndexError, match="no-such-skill"):
        evaluate(searcher, [("q", ["no-such-skill"])], 5, "keyword")


def test_shipped_queries_only_name_fixture_skills(skills_dir, queries_file, tmp_path):
    searcher = Searcher(scan([skills_dir]), tmp_path)
    report = evaluate(searcher, load_queries(queries_file), 5, "keyword")
    assert report.queries >= 20


def test_load_queries_reports_the_bad_line(tmp_path):
    bad = tmp_path / "q.jsonl"
    bad.write_text('{"query": "ok", "expected": "a"}\n{"query": "no expected"}\n', encoding="utf-8")
    with pytest.raises(SkillIndexError, match="q.jsonl:2"):
        load_queries(bad)


def test_parse_ranking_drops_out_of_range_and_repeats():
    assert parse_ranking("3, 1, 3, 99, 2", size=5, k=5) == [2, 0, 1]
    assert parse_ranking("2, 4, 5", size=5, k=2) == [1, 3]
    assert parse_ranking("none", size=5, k=2) == []


def test_ollama_client_maps_failures_to_one_error(monkeypatch):
    from skillsonar._http import HttpFailure

    def refuse(*args, **kwargs):
        raise HttpFailure("connection refused")

    monkeypatch.setattr("skillsonar.ollama.post_json", refuse)
    with pytest.raises(OllamaError, match="is the embeddings server running"):
        OllamaClient().embed_documents(["x"])


def test_ollama_client_names_the_missing_model_on_404(monkeypatch):
    from skillsonar._http import HttpFailure

    def missing(*args, **kwargs):
        raise HttpFailure("HTTP 404", 404)

    monkeypatch.setattr("skillsonar.ollama.post_json", missing)
    with pytest.raises(OllamaError, match="does not know model embeddinggemma-2"):
        OllamaClient().embed_query("x")


def test_ollama_host_without_scheme_is_accepted(monkeypatch):
    monkeypatch.setenv("SKILLSONAR_EMBED_HOST", "10.0.0.5:11436")
    assert OllamaClient.from_env().host == "http://10.0.0.5:11436"
    monkeypatch.delenv("SKILLSONAR_EMBED_HOST")
    monkeypatch.setenv("OLLAMA_HOST", "10.0.0.5:11434")
    assert OllamaClient.from_env().host == "http://127.0.0.1:11436"


def test_ollama_client_sends_prefixed_openai_requests(monkeypatch):
    sent = []

    def reply(url, payload, **kwargs):
        sent.append((url, payload))
        rows = [{"index": i, "embedding": [float(i)]} for i in range(len(payload["input"]))]
        return {"data": rows[::-1]}

    monkeypatch.setattr("skillsonar.ollama.post_json", reply)
    client = OllamaClient("http://h:1")
    assert client.embed_documents(["a", "b"]) == [[0.0], [1.0]]
    assert client.embed_query("q") == [0.0]
    assert [u for u, _ in sent] == ["http://h:1/v1/embeddings"] * 2
    assert sent[0][1] == {
        "model": "embeddinggemma-2",
        "input": ["title: none | text: a", "title: none | text: b"],
    }
    assert sent[1][1]["input"] == ["task: search result | query: q"]


def test_embeddings_built_with_another_model_are_refused(tmp_path):
    save_embeddings(tmp_path, {"model": "bge-m3", "count": 1, "paths": ["/p"], "vectors": [[1.0]]})
    with pytest.raises(SkillIndexError, match="built with bge-m3, not embeddinggemma-2"):
        load_embeddings(tmp_path, [{"path": "/p"}], "embeddinggemma-2")
    assert load_embeddings(tmp_path, [{"path": "/p"}], "bge-m3") == {"/p": [1.0]}


def test_rerank_client_requires_configuration(monkeypatch):
    monkeypatch.delenv("SKILLSONAR_RERANK_BASE_URL", raising=False)
    monkeypatch.delenv("SKILLSONAR_RERANK_MODEL", raising=False)
    with pytest.raises(RerankError, match="SKILLSONAR_RERANK_BASE_URL"):
        RerankClient.from_env()


def test_rerank_client_sends_openai_chat_request(monkeypatch):
    sent = {}

    def fake_post(url, payload, headers=None, timeout=0):
        sent.update(url=url, payload=payload, headers=headers)
        return {"choices": [{"message": {"content": "2, 1"}}]}

    monkeypatch.setattr("skillsonar.rerank.post_json", fake_post)
    client = RerankClient("https://example.test/v1/", "m", "secret")
    assert client.rank("task", ["a: x", "b: y"], 2) == [1, 0]
    assert sent["url"] == "https://example.test/v1/chat/completions"
    assert sent["headers"] == {"Authorization": "Bearer secret"}
    assert "1. a: x" in sent["payload"]["messages"][0]["content"]


def test_rerank_client_rejects_empty_answer(monkeypatch):
    monkeypatch.setattr(
        "skillsonar.rerank.post_json",
        lambda *a, **k: {"choices": [{"message": {"content": None}}]},
    )
    with pytest.raises(RerankError, match="empty"):
        RerankClient("https://example.test/v1", "m").rank("q", ["a"], 1)
