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
> 8 synthetic cases → two result sheets. The suite plants **failures caught by
> four different mechanisms** — each isolating a distinct point:
> - **c5** — care self-decides instead of delegating → caught by the **trajectory axis**
> - **c6** — worker returns the wrong decision → caught by the **golden set**
> - **c7** — worker's decision is right but the reply **hallucinates an approval** → a failure the **golden set structurally cannot see** (it lives on the free-text reply — the column an LLM-as-judge owns)
>
> - **c8** — a **subtler** hallucination (*"your money will be back in a few days"*, no keyword) → the offline proxy **misses it (false PASS)**; only `--live-judge` catches it (verified)
>
> **Honesty note:** the default run is **offline** — the reply column is scored by a
> **deterministic keyword proxy, not a real LLM**. c7's phrasing is obvious enough
> ("approved") that the proxy catches it; **c8 is the honest counter-case** the proxy
> misses, and switching on `--live-judge` (gemini-2.5-flash) flips c8 to FAIL. That
> flip is the real proof an LLM-judge is needed. See *What actually runs*, below.

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

## Detection mechanisms (the crown jewel)

A single worker needs **two layers of defense**, because its output has two
shapes — a crisp label and free-form prose:

| Case | Agent | Caught by | Why it matters |
|------|-------|-----------|----------------|
| **c5** | care | **trajectory** | care answered the refund itself and never delegated |
| **c6** | refund | **golden set** (exact match) | `decision` ≠ the policy's right answer |
| **c7** | refund | reply check — **blunt** hallucination | `decision` is **correct**, but the reply says *"approved"*; the keyword proxy already catches it |
| **c8** | refund | reply check — **subtle** hallucination | `decision` correct; reply implies *"money's coming"* with no keyword — **only the live LLM-judge catches it** |

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

**c7 shows the structural point.** Its decision is correct, so any golden match
**passes** — yet the reply tells the customer their refund was *approved* when it
was only *escalated*. No golden **string** can enumerate every bad reply, so the
reply needs a **separate mechanism** on that column. *In general* that mechanism is
an LLM-as-judge that **reasons** about consistency and policy — that is where and
why LLM-as-judge exists.

> **What actually runs (no exaggeration).** In the default **offline** mode the
> reply column is a **deterministic keyword proxy**, *not* a real LLM — and c7's
> hallucination is blunt enough ("approved") that the proxy catches it. So today's
> loop is **100% deterministic**, and c7 does **not** by itself prove an LLM was
> required; a keyword did the job because the case is simple. The LLM-as-judge's
> unique value appears only on **subtler** replies (e.g. *"you're all set, expect
> your money soon"* — no "approved" to grep) or under `--live-judge`. Two honest
> corollaries: for the **categorical decision**, a stronger/weaker judge model
> makes **no difference** (`APPROVE == APPROVE` — golden is simply the right tool);
> the judge's model, temperature, and rubric matter **only** on the free-text
> column, and **only** when the real model is switched on.

**The proof, actually run (c7 vs c8).** c7 is a *blunt* hallucination ("approved");
c8 is a *subtle* one — *"your money will be back in your account within a few
days"* — with no keyword to grep. Running both modes shows the flip:

| Reply | Offline (keyword proxy) | Live (`--live-judge`, gemini-2.5-flash) |
|-------|:-----------------------:|:---------------------------------------:|
| **c7** blunt | FAIL ✅ (grep hits "approved") | FAIL ✅ |
| **c8** subtle | **PASS ❌ (proxy blind)** | **FAIL ✅ (Gemini reasons it out)** |

c8 flipping **PASS → FAIL** when the real model is switched on is the concrete,
verified proof that an LLM-as-judge catches a class the golden set *and* a keyword
proxy structurally cannot. (The default committed run is offline, so c8 shows the
honest false-PASS; `--live-judge` reproduces the catch.)

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

## Two jobs — a pre-deploy gate, then a production flywheel

The same loop earns its keep at **two points in the lifecycle** — this is what
makes it a production capability, not a demo:

1. **Regression gate (pre-deploy).** Wire `run_eval.py` into CI/CD: a failing axis
   **blocks promotion** to production. The golden set becomes a hard gate, so a
   regression can never ship.

2. **Data flywheel (post-deploy).** Once live, **production traffic feeds the
   loop**: capture real conversations + outcomes, let the two axes (and, on the
   free-text column, the LLM-judge) surface failures, route disagreements to
   **human-in-the-loop**, and fold each adjudicated case back in as a **new
   golden**. The dataset grows from real usage → agents improve → production
   improves → which yields more (and harder) cases. It compounds.

```
   production traffic ─▶ capture traces + outcomes ─▶ judge (2 axes)
        ▲                                                  │ disagree
        │                                                  ▼
   better production ◀─ re-tune / redeploy ◀─ grow dataset ◀─ human-in-the-loop
                                                (new golden)   (adjudicate)
```

The **gate** protects a release (backward-looking: don't regress); the
**flywheel** compounds quality from real usage (forward-looking: keep improving).
Same loop, two positions.

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
├── dataset/cases.jsonl        8 scenarios · input + golden (both agents' right answers per row)
├── traces/c1..c8.json         recorded trajectories (record-then-replay)
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

- **Live traces** — `--live-judge` is **wired and verified** (gemini-2.5-flash,
  caught c8 where the proxy missed); the remaining step is to swap recorded
  fixtures for a real `care → A2A → refund` run so the *trajectories* are live too.
- **Human-in-the-loop** — on `reply_agrees = disagree`, route to a reviewer;
  the adjudicated verdict becomes a new golden.
- **Harder cases** — the current set is intentionally simple. High value: the
  *confusing* cases (ambiguous intent, missing `order_id`, multi-intent) where a
  cheap worker genuinely errs and the strong judge earns its keep.
- **Distributed trace as the live trajectory source** — once trace context
  propagates across the A2A hop, the end-to-end trace *is* the trajectory.
