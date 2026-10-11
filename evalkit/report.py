"""Aggregate graded results into metrics and a Markdown report."""

from __future__ import annotations

import statistics
from collections import Counter

from .graders import ERROR_TYPES
from .runner import Result


def summarize(results: list[Result], labels: list[str], price: dict | None = None) -> dict:
    n = len(results)
    fields = list(results[0].case.expected) if results else []
    errors = Counter(r.grade.error_type for r in results if r.grade.error_type)

    confusion = {gold: Counter() for gold in labels}
    for r in results:
        gold = r.case.expected.get("category")
        pred = (r.grade.parsed or {}).get("category")
        pred = pred.strip().lower() if isinstance(pred, str) else "(none)"
        if gold in confusion:
            confusion[gold][pred if pred in labels else "(other)"] += 1

    per_label = {}
    for label in labels:
        gold_n = sum(confusion[label].values())
        tp = confusion[label][label]
        pred_n = sum(confusion[g][label] for g in labels)
        per_label[label] = {
            "support": gold_n,
            "precision": tp / pred_n if pred_n else 0.0,
            "recall": tp / gold_n if gold_n else 0.0,
        }

    tags = Counter(t for r in results for t in r.case.tags)
    tag_accuracy = {t: sum(r.grade.passed for r in results if t in r.case.tags) / c for t, c in sorted(tags.items())}

    in_tok = sum(r.input_tokens for r in results)
    out_tok = sum(r.output_tokens for r in results)
    cost = None
    if price:
        cost = in_tok / 1e6 * price.get("input_per_mtok", 0) + out_tok / 1e6 * price.get("output_per_mtok", 0)

    latencies = sorted(r.latency_ms for r in results)
    return {
        "cases": n,
        "accuracy": sum(r.grade.passed for r in results) / n if n else 0.0,
        "json_valid": sum(r.grade.parsed is not None for r in results) / n if n else 0.0,
        "field_accuracy": {f: sum(r.grade.field_correct.get(f, False) for r in results) / n for f in fields},
        "errors": {e: errors.get(e, 0) for e in ERROR_TYPES},
        "confusion": {g: dict(c) for g, c in confusion.items()},
        "per_label": per_label,
        "tag_accuracy": tag_accuracy,
        "latency_ms_p50": statistics.median(latencies) if latencies else 0.0,
        "latency_ms_p95": latencies[max(0, int(len(latencies) * 0.95) - 1)] if latencies else 0.0,
        "input_tokens": in_tok,
        "output_tokens": out_tok,
        "cost_usd": cost,
    }


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def render_markdown(name: str, summaries: dict[str, dict], results: dict[str, list[Result]], labels: list[str]) -> str:
    variants = list(summaries)
    out = [f"# Eval report: {name}", ""]

    out += [
        "## Overview",
        "",
        "| Variant | Accuracy | Valid JSON | "
        + " | ".join(f"{f}" for f in summaries[variants[0]]["field_accuracy"])
        + " | p50 latency | Tokens (in/out) | Est. cost |",
        "|---" * (6 + len(summaries[variants[0]]["field_accuracy"])) + "|",
    ]
    for v in variants:
        s = summaries[v]
        cost = f"${s['cost_usd']:.4f}" if s["cost_usd"] is not None else "-"
        out.append(
            f"| `{v}` | **{_pct(s['accuracy'])}** | {_pct(s['json_valid'])} | "
            + " | ".join(_pct(a) for a in s["field_accuracy"].values())
            + f" | {s['latency_ms_p50']:.0f} ms | {s['input_tokens']:,} / {s['output_tokens']:,} | {cost} |"
        )

    out += ["", "## Where it fails", "", "Each failed case gets one error type (first match in this order).", ""]
    out += ["| Error type | " + " | ".join(f"`{v}`" for v in variants) + " |", "|---" * (1 + len(variants)) + "|"]
    for e in ERROR_TYPES:
        out.append(f"| {e} | " + " | ".join(str(summaries[v]["errors"][e]) for v in variants) + " |")

    out += [
        "",
        "## Accuracy by case tag",
        "",
        "| Tag | " + " | ".join(f"`{v}`" for v in variants) + " |",
        "|---" * (1 + len(variants)) + "|",
    ]
    for tag in summaries[variants[0]]["tag_accuracy"]:
        out.append(f"| {tag} | " + " | ".join(_pct(summaries[v]["tag_accuracy"].get(tag, 0)) for v in variants) + " |")

    best = max(variants, key=lambda v: summaries[v]["accuracy"])
    s = summaries[best]
    cols = labels + ["(other)", "(none)"]
    out += [
        "",
        f"## Category confusion matrix (`{best}`)",
        "",
        "Rows are the expected label, columns the predicted one.",
        "",
        "| expected \\ predicted | " + " | ".join(c.replace("_", " ") for c in cols) + " | recall |",
        "|---" * (len(cols) + 2) + "|",
    ]
    for g in labels:
        row = s["confusion"].get(g, {})
        cells = [(f"**{row.get(c, 0)}**" if c == g else str(row.get(c, 0) or "")) for c in cols]
        out.append(f"| {g.replace('_', ' ')} | " + " | ".join(cells) + f" | {_pct(s['per_label'][g]['recall'])} |")

    out += ["", "## Failed cases", ""]
    for v in variants:
        failed = [r for r in results[v] if not r.grade.passed]
        out += [f"### `{v}` ({len(failed)} failed)", ""]
        if not failed:
            out += ["None.", ""]
            continue
        out += ["| Case | Error | Input | Expected | Output |", "|---|---|---|---|---|"]
        for r in failed[:15]:
            exp = ", ".join(f"{k}={val}" for k, val in r.case.expected.items())
            got = r.output.replace("\n", " ").replace("|", "\\|").replace("`", "'")
            out.append(
                f"| {r.case.id} | {r.grade.error_type} | {r.case.input.replace('|', '/')} | {exp} | `{got[:120]}` |"
            )
        if len(failed) > 15:
            out.append(f"| ... | | {len(failed) - 15} more | | |")
        out.append("")
    return "\n".join(out)
