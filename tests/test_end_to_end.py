import json
import subprocess
import sys
from pathlib import Path

from evalkit.cli import main
from evalkit.report import summarize
from evalkit.runner import run_all

ROOT = Path(__file__).resolve().parents[1]


def setup_module():
    subprocess.run([sys.executable, str(ROOT / "scripts" / "simulate_runs.py")], check=True)


def test_every_case_is_scored():
    results = run_all(ROOT / "evals.toml")
    assert set(results) == {"baseline", "few_shot", "few_shot_schema"}
    assert all(len(rs) == 40 for rs in results.values())


def test_confusion_matrix_adds_up():
    labels = [
        "order_status",
        "cancel_order",
        "return_refund",
        "address_change",
        "product_question",
        "payment_issue",
        "complaint",
    ]
    results = run_all(ROOT / "evals.toml", ["few_shot_schema"])["few_shot_schema"]
    s = summarize(results, labels)
    assert sum(sum(row.values()) for row in s["confusion"].values()) == len(results)
    assert sum(s["errors"].values()) == sum(not r.grade.passed for r in results)


def test_prompt_iterations_improve_accuracy():
    results = run_all(ROOT / "evals.toml")
    acc = {name: sum(r.grade.passed for r in rs) / len(rs) for name, rs in results.items()}
    assert acc["baseline"] < acc["few_shot"] < acc["few_shot_schema"]


def test_cli_run_and_gate(tmp_path):
    out = tmp_path / "reports"
    assert main(["run", "--config", str(ROOT / "evals.toml"), "--out", str(out)]) == 0
    assert (out / "report.md").read_text().startswith("# Eval report")
    assert main(["check", "--config", str(ROOT / "evals.toml"), "--summary", str(out / "summary.json")]) == 0

    # A regression below the threshold must fail the gate.
    summary = json.loads((out / "summary.json").read_text())
    summary["few_shot_schema"]["accuracy"] = 0.5
    (out / "summary.json").write_text(json.dumps(summary))
    assert main(["check", "--config", str(ROOT / "evals.toml"), "--summary", str(out / "summary.json")]) == 1
