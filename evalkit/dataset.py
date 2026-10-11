"""Load evaluation cases from JSON Lines."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Case:
    id: str
    input: str
    expected: dict
    tags: list[str] = field(default_factory=list)


def load_cases(path: str | Path) -> list[Case]:
    cases: list[Case] = []
    seen: set[str] = set()
    with Path(path).open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row["id"] in seen:
                raise ValueError(f"{path}:{line_no}: duplicate case id {row['id']}")
            seen.add(row["id"])
            cases.append(Case(row["id"], row["input"], row["expected"], row.get("tags", [])))
    return cases
