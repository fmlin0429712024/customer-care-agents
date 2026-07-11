# Evaluation Loop & Regression Testing — a localhost QA gate

*How do you know the two-agent system is correct? This is the **QA gate**, not a
runtime harness: it runs on **localhost**, sits **in front of deploy**, and is
**never itself deployed**. It audits the system **end-to-end**, localizes **which
agent** failed, and uses an **LLM-as-judge** exactly where a golden answer
structurally cannot reach.*

Unlike [Way 1](harness-cloud-run.md) / [Way 2](harness-agent-platform.md)
(*where* the agents run), evaluation is **orthogonal to deployment** — it neither
needs Cloud Run nor Agent Engine, and it needs **neither Cloud Trace nor
LangSmith** (see *Where the trajectory comes from*, below).

> **✅ Runs locally, zero external deps:** `python3 eval/run_eval.py`
> 7 synthetic cases → two result sheets. The suite catches **three planted
> failures, each by a different mechanism** — the whole point:
> - **c5** — care self-decides instead of delegating → caught by the **trajectory axis**
> - **c6** — worker returns the wrong decision → caught by the **golden set**
> - **c7** — worker's decision is right but the reply **hallucinates an approval** → caught **only by the LLM-as-judge**

```
   dataset/cases.jsonl        traces/*.json          judge.py              results/
   (input + golden)     ->   (what the agents  ->   2 axes:          ->   care_trajectory.csv
   one row per scenario      actually did)          trajectory + outcome   refund_outcome.csv
```

---

## Why end-to-end (not unit-testing each agent)

The testing pyramid still applies — but the interesting bug lives at the top:

- **Unit / component** (cheap, many): test each agent in isolation.
- **End-to-end** (few, this suite): drive `care → A2A → refund` as one system.

E2E earns its place because the **A2A seam is exactly what unit tests cannot
reach** — whether care passes the `order_id` in the right shape, and whether it
**delegates instead of inventing its own refund decision**. So the design is
**one run, judged on two axes** — and the axis that fails tells you **which agent
is at fault** (fault localization for free).

## Two axes = the two agent archetypes

| Axis | Agent | Evaluates | How |
|------|-------|-----------|-----|
| **Trajectory** | care (coordinator) | *did it get there the right way?* — route, slot-fill, **no self-decision** | deterministic checks over the trajectory |
| **Outcome** | refund (worker) | *is the answer right?* — decision + the customer reply | golden match **+** LLM-as-judge |

## Three detection mechanisms (the crown jewel)

A single worker needs **two layers of defense**, because its output has two
shapes — a crisp label and free-form prose:

| Case | Agent | Caught by | Why it matters |
|------|-------|-----------|----------------|
| **c5** | care | **trajectory** | care answered the refund itself and never delegated |
| **c6** | refund | **golden set** (exact match) | `decision` ≠ the policy's right answer |
| **c7** | refund | **LLM-as-judge** | `decision` is **correct**, but the reply promises an approval that never happened |

*(c5 also shows FAIL on the outcome axis — a realistic **cascade**: because care
never delegated, the worker was never invoked, so no decision exists to score.
Its **primary** signal is the trajectory axis; a coordinator miss starves the
worker downstream.)*

The load-bearing distinction (and the most common interview trap):

> **Exact-match against a golden set is *not* LLM-as-judge — it's an assertion.**
> There is no LLM judging in `decision == golden`.

So each mechanism guards a different output shape:

| Output shape | Mechanism | Is it LLM-as-judge? |
|--------------|-----------|:-------------------:|
| **crisp / categorical** (`APPROVE`/`ESCALATE`/`REJECT`) | golden exact match | ❌ assertion |
| **free-form text** (the customer reply — tone, false promises, hallucination) | **LLM-as-judge** vs a rubric | ✅ |

**c7 is the proof.** Its decision is correct, so any golden match **passes** —
yet the reply tells the customer their refund was *approved* when it was only
*escalated*. No golden **string** can enumerate every bad reply; only a judge that
**reasons** about consistency and policy can catch it. That is where — and why —
LLM-as-judge exists.

> **Why a judge can catch what the worker missed:** not "a bigger model," but
> **verification is easier than generation** (grading < solving). The judge is
> handed the reference, sees the full trajectory, and has a narrower job — so even
> a modest judge catches errors a busy generator makes. This is also why the
> production pattern *cheap worker + strong judge* is rational: generation is the
> high-volume expensive path; verification is occasional and intrinsically easier.

## Pass / fail — and the door to human-in-the-loop

**Pass = the evaluator AGREES with what the agent did. Fail = disagreement.**
Disagreement is exactly the **human-in-the-loop** trigger (a reviewer adjudicates,
and the verdict becomes a new golden) — designed-for here, implemented next.

## Where the trajectory comes from (a deliberate clarification)

Two different meanings of "trace" are easy to conflate:

| | runtime trace (Cloud Trace / LangSmith) | **eval trajectory (here)** |
|---|---|---|
| purpose | debug / monitor a live run | **score a test case** |
| belongs to | the harness (Way 1/2) | the eval loop |
| source now | — | recorded fixtures in `traces/*.json` |

The trajectory is **captured from the agent run**, not pulled from an
observability backend. Today it's a **recorded fixture** (record-then-replay), so
the scoring loop is **deterministic and reviewable**; flip to live by
regenerating `traces/` from the real run — **the judge is unchanged**.

## Folder layout

```
eval/                          ← workspace-level: holistic, spans BOTH agents
├── dataset/cases.jsonl        7 scenarios · input + golden (both agents' right answers per row)
├── traces/c1..c7.json         recorded trajectories (record-then-replay)
├── judge.py                   judge_care (trajectory) · judge_refund (golden + LLM-judge)
├── run_eval.py                loop entry → 2 CSVs + summary
└── results/*.csv              care_trajectory.csv · refund_outcome.csv
```

Each dataset row carries **both agents' golden** in one place — `expected_delegate`
(care's reference) and `golden_decision` (refund's reference) — because it is a
single end-to-end journey judged on two axes.

## Run it

```bash
cd eval
python3 run_eval.py                # offline: deterministic judge proxy, zero deps
python3 run_eval.py --live-judge   # use Gemini as the reply judge (needs auth)
```

## Gaps (honest) — next steps

- **Live judge & live traces** — swap recorded fixtures for a real
  `care → A2A → refund` run; `--live-judge` already wires the Gemini path.
- **Human-in-the-loop** — on `reply_agrees = disagree`, route to a reviewer;
  the adjudicated verdict becomes a new golden.
- **Harder cases** — the current set is intentionally simple. High value: the
  *confusing* cases (ambiguous intent, missing `order_id`, multi-intent) where a
  cheap worker genuinely errs and the strong judge earns its keep.
- **Distributed trace as the live trajectory source** — once trace context
  propagates across the A2A hop, the end-to-end trace *is* the trajectory.
