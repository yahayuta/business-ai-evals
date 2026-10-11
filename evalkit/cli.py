"""Command line entry point.

python -m evalkit run   --config evals.toml [--variant NAME ...] [--out reports]
python -m evalkit check --config evals.toml [--summary reports/summary.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .report import render_markdown, summarize
from .runner import load_config, run_all


def cmd_run(args) -> int:
    config = load_config(args.config)
    labels = config["eval"]["labels"]
    prices = {v["name"]: v.get("price") for v in config["variants"]}

    results = run_all(args.config, args.variant)
    summaries = {name: summarize(rs, labels, prices.get(name)) for name, rs in results.items()}

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(summaries, indent=2), encoding="utf-8")
    (out / "report.md").write_text(
        render_markdown(config["eval"]["name"], summaries, results, labels) + "\n", encoding="utf-8"
    )
    with (out / "results.jsonl").open("w", encoding="utf-8") as f:
        for name, rs in results.items():
            for r in rs:
                f.write(
                    json.dumps(
                        {
                            "variant": name,
                            "case_id": r.case.id,
                            "passed": r.grade.passed,
                            "error_type": r.grade.error_type,
                            "output": r.output,
                        }
                    )
                    + "\n"
                )

    for name, s in summaries.items():
        print(f"{name:<20} accuracy={s['accuracy']:.3f} json_valid={s['json_valid']:.3f}")
    print(f"report written to {out / 'report.md'}")
    return 0


def cmd_check(args) -> int:
    """Quality gate: fail (exit 1) when the release variant drops below thresholds."""
    gate = load_config(args.config).get("gate", {})
    summaries = json.loads(Path(args.summary).read_text(encoding="utf-8"))
    s = summaries.get(gate["variant"])
    if s is None:
        print(f"gate variant '{gate['variant']}' not found in {args.summary}")
        return 1

    checks = [
        ("accuracy", s["accuracy"], gate.get("min_accuracy", 0)),
        ("json_valid", s["json_valid"], gate.get("min_json_valid", 0)),
    ] + [(f"field_accuracy.{f}", s["field_accuracy"][f], v) for f, v in gate.get("min_field_accuracy", {}).items()]

    ok = True
    for name, value, minimum in checks:
        status = "PASS" if value >= minimum else "FAIL"
        ok &= status == "PASS"
        print(f"[{status}] {gate['variant']} {name} = {value:.3f} (min {minimum:.3f})")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="evalkit", description="Evaluate business LLM tasks.")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="run variants and write a report")
    run.add_argument("--config", default="evals.toml")
    run.add_argument("--variant", action="append", help="run only this variant (repeatable)")
    run.add_argument("--out", default="reports")
    run.set_defaults(func=cmd_run)

    check = sub.add_parser("check", help="quality gate for CI")
    check.add_argument("--config", default="evals.toml")
    check.add_argument("--summary", default="reports/summary.json")
    check.set_defaults(func=cmd_check)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
