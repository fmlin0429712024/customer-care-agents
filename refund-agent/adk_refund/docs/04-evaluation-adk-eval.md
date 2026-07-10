# 04 — Evaluation: `adk eval` (offline regression gate)

**Status: ✅ Done.** Turned the test scenarios into an ADK **eval set** (golden
set) and ran `adk eval` **locally / offline** — the pre-deploy regression gate.
4/4 cases passed. This is the flywheel's first turnkey gear.

---

## What eval is (and isn't)

`adk eval` is **offline regression testing** for the *non-deterministic* part of
the agent. It runs the whole agent end-to-end against fixed cases with known
answers and scores the result against thresholds — it does **not** run on live
traffic. It runs in CI **before** deploy.

| | Runtime cross-check (a flow you build) | **`adk eval`** |
|---|---|---|
| When | production, per request | dev / CI, offline, before deploy |
| Input | real live request | fixed golden set |
| Purpose | catch live hallucination → human | catch regressions → block release |

---

## Two metrics = the deterministic / non-deterministic split, made visible

| Metric | Dimension | Our result |
|--------|-----------|-----------|
| `tool_trajectory_avg_score` (threshold 1.0) | **deterministic** — did it call the right tools in order | **1.0 on all 4** |
| `response_match_score` (threshold 0.8, ROUGE) | **non-deterministic** — wording similarity | **0.85–1.0** (varies, absorbed by threshold) |

| Case | tool traj | response match | verdict |
|------|-----------|----------------|---------|
| auto-approve | 1.0 | 0.926 | ✅ |
| past-window | 1.0 | 0.951 | ✅ |
| in-transit | 1.0 | 0.848 | ✅ |
| not-found | 1.0 | 1.0 | ✅ |

`in-transit` (0.848) is closest to the 0.8 line — if a SKILL.md change drifts
the wording further, it drops below threshold → FAIL → regression caught. That
is the gate working. **Thresholds absorb LLM non-determinism**; you don't demand
byte-exact output, you demand "score ≥ threshold."

Keep deterministic logic (`tools.py`) on **traditional unit tests** (exact, fast);
use `adk eval` for the **end-to-end, non-deterministic** behavior. Test pyramid:
many fast unit tests below, fewer end-to-end evals on top. `adk eval` does not
replace unit tests — unit tests localize *where* a failure is.

---

## How to run

```bash
pip install "google-adk[eval]"          # one-time: rouge-score, etc.

# golden set was bootstrapped "record then replay": run the agent once on the
# verified cases, capture final_response + tool_uses, save as refund_golden.evalset.json
export GOOGLE_API_KEY=... GOOGLE_GENAI_USE_VERTEXAI=FALSE GOOGLE_CLOUD_PROJECT=linkhealth-care-2024
adk eval refund_agent refund_golden.evalset.json
```

Optional `--config_file_path` sets custom thresholds
(`{"criteria": {"tool_trajectory_avg_score": 1.0, "response_match_score": 0.7}}`);
`--print_detailed_results` prints per-case detail. Results are also written to
`refund_agent/.adk/eval_history/*.evalset_result.json`.

---

## Scope note: only cases 1–4

The 7 scenarios in `reference/test-scenarios.json` all run through the LLM (all
non-deterministic). Cases 1–4 run with current data. Cases 5–7 (high-value,
duplicate, fraud) need **synthetic data** first (an order `HIGH001`, seeded
tickets) — deferred. Lesson: eval cases must match the environment's data.

---

## Where it fits: CI gate before deploy

```
PR / commit → CI: adk eval (offline)  ── pass → deploy (Cloud Run)
                                        └─ fail → block (regression)
```

Eval is **local/offline** and logically runs **before** deployment — even though
our learning path did Cloud Run first. It is the first turnkey gear of the data
flywheel (observability → eval gate → feedback → improve → redeploy).

---

## The one concept to remember

> `adk eval` = offline regression testing for the non-deterministic layer, with
> **thresholds** instead of exact match. Tool trajectory checks the deterministic
> path (exact); response match tolerates wording. It gates the release; it never
> touches live traffic.
