"""End-to-end eval loop for the two-agent system (localhost, no harness).

    dataset (golden)  ->  trajectory traces  ->  judge (2 axes)  ->  2 CSVs

Trajectories live in traces/ as recorded fixtures (record-then-replay), so the
scoring loop is deterministic and reviewable. Flip to live agents later by
regenerating traces/ from the real care -> A2A -> refund run; the judge is
unchanged.

Usage:
    python3 run_eval.py                # offline (deterministic judge)
    python3 run_eval.py --live-judge   # use Gemini as the reply judge
"""
import csv
import json
import sys
from pathlib import Path

from judge import judge_care, judge_refund

ROOT = Path(__file__).parent
CASES = ROOT / "dataset" / "cases.jsonl"
TRACES = ROOT / "traces"
OUT = ROOT / "results"


def load_cases():
    with open(CASES) as f:
        return [json.loads(line) for line in f if line.strip()]


def load_trace(case_id):
    with open(TRACES / f"{case_id}.json") as f:
        return json.load(f)


def main(use_llm=False):
    OUT.mkdir(exist_ok=True)
    cases = load_cases()
    care_rows, refund_rows = [], []

    for c in cases:
        t = load_trace(c["case_id"])
        care_result, _ = judge_care(c, t)
        refund_result, rchecks = judge_refund(c, t, use_llm=use_llm)

        care = t["care"]
        refund = t.get("refund", {}) or {}
        care_rows.append({
            "case_id": c["case_id"],
            "chat": c["chat"],
            "expected_delegate": c["expected_delegate"],
            "actual_delegate": care["delegated_to_refund"],
            "order_expected": c["order_id"] or "-",
            "order_got": care.get("slot_filled_order_id") or "-",
            "made_own_decision": care.get("made_own_decision"),
            "result": care_result,
        })
        refund_rows.append({
            "case_id": c["case_id"],
            "order_id": c["order_id"] or "-",
            "golden_decision": c["golden_decision"] or "-",
            "actual_decision": refund.get("decision", "-") if c["expected_delegate"] else "-",
            "decision_match": rchecks.get("decision_match", "-"),
            "reply_agrees": rchecks.get("reply_agrees", "-"),
            "result": refund_result,
        })

    write_csv(OUT / "care_trajectory.csv", care_rows)
    write_csv(OUT / "refund_outcome.csv", refund_rows)

    print(f"\n  judge mode: {'LIVE Gemini' if use_llm else 'offline (deterministic proxy)'}\n")
    summarize("care   (trajectory axis)", care_rows)
    summarize("refund (outcome axis)   ", refund_rows)
    print("\n  wrote results/care_trajectory.csv + results/refund_outcome.csv\n")


def write_csv(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def summarize(name, rows):
    scored = [r for r in rows if r["result"] in ("PASS", "FAIL")]
    passed = sum(1 for r in scored if r["result"] == "PASS")
    fails = [r["case_id"] for r in scored if r["result"] == "FAIL"]
    tail = f"   (fail: {', '.join(fails)})" if fails else ""
    print(f"  {name}:  {passed}/{len(scored)} pass{tail}")


if __name__ == "__main__":
    main(use_llm="--live-judge" in sys.argv)
