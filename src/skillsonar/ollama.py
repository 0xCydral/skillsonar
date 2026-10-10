"""The only module that talks to Ollama. Everything else asks for embeddings by meaning."""

from __future__ import annotations

import os

from skillsonar._http import HttpFailure, post_json
from skillsonar.errors import OllamaError

DEFAULT_HOST = "http://127.0.0.1:11434"
DEFAULT_MODEL = "bge-m3"


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
            os.environ.get("OLLAMA_HOST") or DEFAULT_HOST,
            os.environ.get("SKILLSONAR_EMBED_MODEL") or DEFAULT_MODEL,
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        """One vector per input text, in order."""
        try:
            data = post_json(
                f"{self.host}/api/embed",
                {"model": self.model, "input": texts},
                timeout=self.timeout,
            )
        except HttpFailure as exc:
            hint = f"run `ollama pull {self.model}`" if exc.status == 404 else "is Ollama running?"
            raise OllamaError(f"embeddings failed at {self.host} ({exc}); {hint}") from exc
        vectors = data.get("embeddings")
        if not isinstance(vectors, list) or len(vectors) != len(texts):
            raise OllamaError(f"unexpected embeddings response from {self.host}")
        return vectors
