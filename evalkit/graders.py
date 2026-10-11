"""Turn a raw model response into a graded result.

A response passes only when it is valid JSON and every expected field matches
after normalisation. When it fails, it gets exactly one error type so failures
can be counted and prioritised (see ERROR_TYPES for the precedence).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

# Ordered by precedence: the first one that applies is reported.
ERROR_TYPES = [
    "invalid_json",  # the output could not be parsed as a JSON object
    "missing_field",  # a required key is absent
    "invalid_label",  # category is not one of the allowed labels
    "wrong_category",  # routing mistake: valid label, wrong choice
    "wrong_order_id",  # extraction mistake (missed, hallucinated or mis-normalised)
    "wrong_sentiment",
]

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)
_ORDER_DIGITS = re.compile(r"(\d{4,})")


@dataclass
class Grade:
    passed: bool
    error_type: str | None
    parsed: dict | None
    field_correct: dict[str, bool] = field(default_factory=dict)


def parse_json(text: str) -> dict | None:
    """Parse a JSON object, tolerating markdown fences and surrounding prose."""
    cleaned = _FENCE.sub("", text.strip())
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end <= start:
            return None
        try:
            value = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            return None
    return value if isinstance(value, dict) else None


def normalize_order_id(value) -> str | None:
    """'#10234', 'order 10234', 'ord-10234' -> 'ORD-10234'. Empty -> None."""
    if value is None:
        return None
    text = str(value).strip()
    if text.lower() in {"", "null", "none", "n/a"}:
        return None
    match = _ORDER_DIGITS.search(text)
    return f"ORD-{match.group(1)}" if match else text.upper()


def _normalize(field_name: str, value):
    if field_name == "order_id":
        return normalize_order_id(value)
    if isinstance(value, str):
        return value.strip().lower()
    return value


def grade(expected: dict, response: str, labels: list[str]) -> Grade:
    parsed = parse_json(response)
    if parsed is None:
        return Grade(False, "invalid_json", None, {k: False for k in expected})

    field_correct = {k: k in parsed and _normalize(k, parsed[k]) == _normalize(k, expected[k]) for k in expected}

    if any(k not in parsed for k in expected):
        error = "missing_field"
    elif "category" in expected and _normalize("category", parsed["category"]) not in labels:
        error = "invalid_label"
    else:
        error = next(
            (f"wrong_{k}" for k in ("category", "order_id", "sentiment") if k in expected and not field_correct[k]),
            None,
        )
    return Grade(error is None, error, parsed, field_correct)
