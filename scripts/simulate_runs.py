"""Create recorded responses for the three prompt variants.

These are SIMULATED outputs, not responses from a real model. They let the
harness, the report and the CI gate run end to end without an API key, and
they reproduce failure patterns commonly seen when iterating on prompts:

* baseline        - free-form answers: prose around the JSON, missing keys,
                    invented order IDs, confusion on ambiguous requests
* few_shot        - examples fix the format most of the time
* few_shot_schema - explicit schema and decision rules remove format errors
                    and most routing mistakes

Replace them with real runs by switching a variant's provider to "openai" or
"anthropic" in evals.toml.

Usage: python scripts/simulate_runs.py
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evalkit.dataset import load_cases

CONFUSABLE = {
    "cancel_order": "return_refund",
    "return_refund": "complaint",
    "complaint": "return_refund",
    "product_question": "complaint",
    "order_status": "complaint",
    "address_change": "order_status",
    "payment_issue": "return_refund",
}

PROFILES = {
    #                 seed  prose  invalid  missing  ambig_wrong  other_wrong  invent_id  drop_id  sentiment
    "baseline": (1, 0.30, 0.08, 0.06, 0.60, 0.08, 0.40, 0.10, 0.15),
    "few_shot": (2, 0.05, 0.03, 0.00, 0.40, 0.03, 0.15, 0.03, 0.08),
    "few_shot_schema": (3, 0.00, 0.00, 0.00, 0.10, 0.00, 0.00, 0.00, 0.03),
}


def simulate(case, variant: str, rng: random.Random) -> dict:
    _, prose, invalid, missing, ambig_wrong, other_wrong, invent_id, drop_id, sent_wrong = PROFILES[variant]
    exp = dict(case.expected)
    out = dict(exp)

    wrong_rate = ambig_wrong if "ambiguous" in case.tags else other_wrong
    if rng.random() < wrong_rate:
        out["category"] = CONFUSABLE[exp["category"]]
    if exp["order_id"] is None and rng.random() < invent_id:
        out["order_id"] = f"ORD-{rng.randint(10000, 12999)}"
    elif exp["order_id"] and rng.random() < drop_id:
        out["order_id"] = None
    elif exp["order_id"] and "id_format" in case.tags and variant == "baseline" and rng.random() < 0.5:
        out["order_id"] = "#" + exp["order_id"].split("-")[1]  # still correct after normalisation
    if rng.random() < sent_wrong:
        out["sentiment"] = {"neutral": "negative", "negative": "neutral", "positive": "neutral"}[exp["sentiment"]]

    text = json.dumps(out)
    roll = rng.random()
    if roll < invalid:
        text = f"Category: {out['category']}. The customer sounds {out['sentiment']}."
    elif roll < invalid + missing:
        out.pop("sentiment")
        text = json.dumps(out)
    elif roll < invalid + missing + prose:
        text = f"Sure! Here is the classification:\n```json\n{text}\n```"

    prompt_tokens = len((ROOT / "prompts" / f"{variant}.txt").read_text()) // 4 + len(case.input) // 4
    return {
        "case_id": case.id,
        "output": text,
        "latency_ms": round(rng.uniform(350, 900) + prompt_tokens * 0.4, 1),
        "input_tokens": prompt_tokens,
        "output_tokens": len(text) // 4,
    }


def main() -> None:
    cases = load_cases(ROOT / "datasets" / "support_tickets.jsonl")
    out_dir = ROOT / "runs"
    out_dir.mkdir(exist_ok=True)
    for variant, profile in PROFILES.items():
        rng = random.Random(profile[0])
        path = out_dir / f"simulated_{variant}.jsonl"
        with path.open("w", encoding="utf-8") as f:
            for case in cases:
                f.write(json.dumps(simulate(case, variant, rng)) + "\n")
        print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
