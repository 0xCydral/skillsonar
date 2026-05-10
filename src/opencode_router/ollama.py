"""Tiny Ollama HTTP client (stdlib-only)."""

from __future__ import annotations

import json
import os
import urllib.request

DEFAULT_URL = os.environ.get("OPENCODE_ROUTER_OLLAMA_URL", "http://localhost:11434")
DEFAULT_EMBED_MODEL = os.environ.get(
    "OPENCODE_ROUTER_EMBED_MODEL", "mxbai-embed-large"
)
DEFAULT_RERANK_MODEL = os.environ.get(
    "OPENCODE_ROUTER_RERANK_MODEL", "qwen3.5:4b"
)


def _post(path: str, payload: dict, *, timeout: int = 60) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{DEFAULT_URL}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def embed(text: str, *, model: str | None = None) -> list[float]:
    body = _post(
        "/api/embeddings",
        {"model": model or DEFAULT_EMBED_MODEL, "prompt": text},
        timeout=30,
    )
    vec = body.get("embedding")
    if not vec:
        raise RuntimeError(f"Ollama returned no embedding: {body}")
    return vec


def generate(
    prompt: str,
    *,
    model: str | None = None,
    json_format: bool = False,
    think: bool = False,
    temperature: float = 0.0,
    num_predict: int = 200,
    timeout: int = 120,
) -> str:
    payload = {
        "model": model or DEFAULT_RERANK_MODEL,
        "prompt": prompt,
        "stream": False,
        "think": think,
        "options": {"temperature": temperature, "num_predict": num_predict},
    }
    if json_format:
        payload["format"] = "json"
    body = _post("/api/generate", payload, timeout=timeout)
    return (body.get("response") or "").strip()


def is_running() -> bool:
    try:
        urllib.request.urlopen(f"{DEFAULT_URL}/api/tags", timeout=2)
        return True
    except Exception:  # noqa: BLE001 — we just want a bool
        return False
