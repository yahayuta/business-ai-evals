"""Run every case of a dataset through one prompt variant and grade it."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from .dataset import Case, load_cases
from .graders import Grade, grade
from .providers import build_provider


@dataclass
class Result:
    variant: str
    case: Case
    output: str
    grade: Grade
    latency_ms: float
    input_tokens: int
    output_tokens: int


def load_config(path: str | Path) -> dict:
    with Path(path).open("rb") as f:
        return tomllib.load(f)


def render_prompt(template: str, case: Case) -> str:
    return template.replace("{input}", case.input)


def run_variant(config: dict, variant: dict, base_dir: Path) -> list[Result]:
    eval_cfg = config["eval"]
    cases = load_cases(base_dir / eval_cfg["dataset"])
    template = (base_dir / variant["prompt"]).read_text(encoding="utf-8")
    provider = build_provider(variant, base_dir)

    results = []
    for case in cases:
        completion = provider.complete(render_prompt(template, case), case)
        results.append(
            Result(
                variant=variant["name"],
                case=case,
                output=completion.text,
                grade=grade(case.expected, completion.text, eval_cfg["labels"]),
                latency_ms=completion.latency_ms,
                input_tokens=completion.input_tokens,
                output_tokens=completion.output_tokens,
            )
        )
    return results


def run_all(config_path: str | Path, only: list[str] | None = None) -> dict[str, list[Result]]:
    config_path = Path(config_path)
    config = load_config(config_path)
    base_dir = config_path.parent
    return {v["name"]: run_variant(config, v, base_dir) for v in config["variants"] if not only or v["name"] in only}
