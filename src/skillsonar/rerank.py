"""The only module that talks to the rerank model (any OpenAI-compatible chat endpoint)."""

from __future__ import annotations

import os
import re

from skillsonar._http import HttpFailure, post_json
from skillsonar.errors import RerankError

PROMPT = """You are choosing which of these skills would help with a task.

Task: {query}

Skills:
{catalog}

Reply with the numbers of the {k} most useful skills, best first, separated by commas.
Numbers only. If fewer than {k} are relevant, list only those.

Answer:"""


class RerankClient:
    def __init__(self, base_url: str, model: str, api_key: str = "", timeout: float = 180):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout

    @classmethod
    def from_env(cls) -> RerankClient:
        base_url = os.environ.get("SKILLSONAR_RERANK_BASE_URL", "")
        model = os.environ.get("SKILLSONAR_RERANK_MODEL", "")
        if not base_url or not model:
            raise RerankError(
                "rerank is not configured: set SKILLSONAR_RERANK_BASE_URL "
                "(for example https://api.openai.com/v1) and SKILLSONAR_RERANK_MODEL; "
                "SKILLSONAR_RERANK_API_KEY is optional for local servers"
            )
        return cls(base_url, model, os.environ.get("SKILLSONAR_RERANK_API_KEY", ""))

    def rank(self, query: str, candidates: list[str], k: int) -> list[int]:
        """Indices into `candidates` (0-based), best first, at most k. Empty if unparseable."""
        catalog = "\n".join(f"{n}. {line}" for n, line in enumerate(candidates, 1))
        prompt = PROMPT.format(query=query, catalog=catalog, k=k)
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        try:
            data = post_json(
                f"{self.base_url}/chat/completions",
                {
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0,
                    "max_tokens": 4000,
                },
                headers,
                self.timeout,
            )
            content = data["choices"][0]["message"]["content"]
        except HttpFailure as exc:
            raise RerankError(f"rerank failed at {self.base_url} ({exc})") from exc
        except (KeyError, IndexError, TypeError) as exc:
            raise RerankError(f"unexpected rerank response from {self.base_url}") from exc
        if not content:
            raise RerankError(f"rerank model {self.model} returned an empty answer")
        return parse_ranking(content, len(candidates), k)


def parse_ranking(answer: str, size: int, k: int) -> list[int]:
    """Read candidate numbers out of a model answer. Out-of-range and repeated numbers are dropped."""
    picked: list[int] = []
    for token in re.findall(r"[0-9]+", answer):
        n = int(token)
        if 1 <= n <= size and n - 1 not in picked:
            picked.append(n - 1)
        if len(picked) >= k:
            break
    return picked
