"""The only module that talks to the embeddings server. Everything else asks for embeddings by meaning.

The server is any OpenAI-shaped `/v1/embeddings` endpoint: the EmbeddingGemma 2 llama.cpp container by
default, and Ollama serves the same route. EmbeddingGemma 2 is task-prefixed and a query embedded without
its prefix ranks worse, so documents and queries go through different methods.
"""

from __future__ import annotations

import os

from skillsonar._http import HttpFailure, post_json
from skillsonar.errors import OllamaError

DEFAULT_HOST = "http://127.0.0.1:11436"
DEFAULT_MODEL = "embeddinggemma-2"
DOCUMENT_PREFIX = "title: none | text: "
QUERY_PREFIX = "task: search result | query: "


class OllamaClient:
    def __init__(self, host: str = DEFAULT_HOST, model: str = DEFAULT_MODEL, timeout: float = 120):
        host = host.strip().rstrip("/")
        if "://" not in host:
            host = "http://" + host
        self.host = host
        self.model = model
        self.timeout = timeout

    @classmethod
    def from_env(cls) -> OllamaClient:
        return cls(
            # Not OLLAMA_HOST: that one points at a real Ollama, which does not serve this model.
            os.environ.get("SKILLSONAR_EMBED_HOST") or DEFAULT_HOST,
            os.environ.get("SKILLSONAR_EMBED_MODEL") or DEFAULT_MODEL,
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """One vector per skill document, in order."""
        return self._embed([DOCUMENT_PREFIX + t for t in texts])

    def embed_query(self, text: str) -> list[float]:
        return self._embed([QUERY_PREFIX + text])[0]

    def _embed(self, texts: list[str]) -> list[list[float]]:
        try:
            data = post_json(
                f"{self.host}/v1/embeddings",
                {"model": self.model, "input": texts},
                timeout=self.timeout,
            )
        except HttpFailure as exc:
            hint = (
                f"the server does not know model {self.model}"
                if exc.status == 404
                else "is the embeddings server running?"
            )
            raise OllamaError(f"embeddings failed at {self.host} ({exc}); {hint}") from exc
        rows = data.get("data")
        if not isinstance(rows, list) or len(rows) != len(texts):
            raise OllamaError(f"unexpected embeddings response from {self.host}")
        try:
            return [row["embedding"] for row in sorted(rows, key=lambda row: row["index"])]
        except (KeyError, TypeError) as exc:
            raise OllamaError(f"unexpected embeddings response from {self.host}") from exc
