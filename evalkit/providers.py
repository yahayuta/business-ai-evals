"""Model providers.

* ``replay``    - reads recorded responses from a JSONL file. Used in CI and for
                  re-scoring old runs without spending tokens.
* ``openai``    - Chat Completions API (needs OPENAI_API_KEY).
* ``anthropic`` - Messages API (needs ANTHROPIC_API_KEY).

The HTTP providers use only the standard library so the harness has no
dependencies.
"""

from __future__ import annotations

import json
import os
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .dataset import Case


@dataclass
class Completion:
    text: str
    latency_ms: float
    input_tokens: int = 0
    output_tokens: int = 0


class ReplayProvider:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._records: dict[str, dict] = {}
        with self.path.open(encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    row = json.loads(line)
                    self._records[row["case_id"]] = row

    def complete(self, prompt: str, case: Case) -> Completion:
        row = self._records.get(case.id)
        if row is None:
            raise KeyError(f"{self.path}: no recorded response for case {case.id}")
        return Completion(
            row["output"], row.get("latency_ms", 0.0), row.get("input_tokens", 0), row.get("output_tokens", 0)
        )


def _post_json(url: str, headers: dict, payload: dict, timeout: float = 60.0) -> tuple[dict, float]:
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode(), headers={"content-type": "application/json", **headers}
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = json.loads(response.read())
    return body, (time.perf_counter() - started) * 1000


class OpenAIProvider:
    def __init__(self, model: str, json_mode: bool = False):
        self.model, self.json_mode = model, json_mode
        self.api_key = os.environ["OPENAI_API_KEY"]

    def complete(self, prompt: str, case: Case) -> Completion:
        payload = {"model": self.model, "temperature": 0, "messages": [{"role": "user", "content": prompt}]}
        if self.json_mode:
            payload["response_format"] = {"type": "json_object"}
        body, ms = _post_json(
            "https://api.openai.com/v1/chat/completions", {"authorization": f"Bearer {self.api_key}"}, payload
        )
        usage = body.get("usage", {})
        return Completion(
            body["choices"][0]["message"]["content"],
            ms,
            usage.get("prompt_tokens", 0),
            usage.get("completion_tokens", 0),
        )


class AnthropicProvider:
    def __init__(self, model: str, max_tokens: int = 256):
        self.model, self.max_tokens = model, max_tokens
        self.api_key = os.environ["ANTHROPIC_API_KEY"]

    def complete(self, prompt: str, case: Case) -> Completion:
        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": 0,
            "messages": [{"role": "user", "content": prompt}],
        }
        body, ms = _post_json(
            "https://api.anthropic.com/v1/messages",
            {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"},
            payload,
        )
        text = "".join(block.get("text", "") for block in body.get("content", []))
        usage = body.get("usage", {})
        return Completion(text, ms, usage.get("input_tokens", 0), usage.get("output_tokens", 0))


def build_provider(variant: dict, base_dir: Path):
    kind = variant.get("provider", "replay")
    if kind == "replay":
        return ReplayProvider(base_dir / variant["replay_file"])
    if kind == "openai":
        return OpenAIProvider(variant["model"], variant.get("json_mode", False))
    if kind == "anthropic":
        return AnthropicProvider(variant["model"])
    raise ValueError(f"unknown provider: {kind}")
