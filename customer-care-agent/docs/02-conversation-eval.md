# 02 — Evaluating the coordinator (conversation eval)

**Status: 🟡 M1 — method + a runnable minimal eval.** The worker is tested one-shot
(`input → golden answer → exact match`). A conversation agent is a different
species: you grade a **trajectory** (a path of turns) on several **dimensions**,
and some dimensions can't be exact-matched — so you add an **LLM judge**.

---

## The one shift

| | Worker (one-shot) | Coordinator (conversation) |
|---|---|---|
| Unit graded | a single answer | a **trajectory** (many turns) |
| Comparison | exact match to golden | some exact, some **rubric-scored** |
| Judge | `==` | `==` **+ an LLM-as-judge** |

## Any eval answers 3 questions

1. **WHAT** to check — the criteria / dimensions.
2. **HOW** to check — deterministic assertion vs LLM-as-judge.
3. **Against WHAT / WHEN** — a golden set, run as a regression gate.

---

## WHAT — the 6 criteria, split by HOW

**A. Deterministic assertions** (exact match — same style as the worker eval):

| Criterion | Term | Pass condition |
|---|---|---|
| Routed to the right specialist | **intent accuracy** | `intent == refund` (per scenario) |
| Handed off the right payload | **tool-call / action accuracy** | payload `== { intent, order_id }` |
| Relay didn't change the outcome | decision preserved | relayed decision `==` worker's decision |

**B. LLM-as-judge** (rubric-scored — the subjective, un-matchable parts):

| Criterion | Term | What the judge asks |
|---|---|---|
| Relay is truthful to the worker | **faithfulness / groundedness** | Did the reply invent anything the worker didn't return? |
| Asked for missing info | slot-filling behavior | With no `order_id`, did it *ask* rather than guess/invent? |
| Tone & cross-turn consistency | **coherence** | Warm? Any self-contradiction across turns? |

> **Textbook takeaway:** chatbot eval = **deterministic checks for the skeleton +
> an LLM judge for the flesh.** Use both.

---

## HOW — LLM-as-judge (a.k.a. model-graded eval / autorater)

For the subjective criteria, give a second LLM the transcript + the expected
behavior + a **rubric**, and have it return a verdict. Rubric used here:

```
For each criterion, output PASS or FAIL and one sentence of evidence.

faithfulness : FAIL if the reply states any decision, amount, ticket, or policy
               the worker did not return. PASS if every claim traces to the worker.
slot-filling : FAIL if it invented/guessed an order_id, or handed off without one.
               PASS if it asked for the missing order_id before handing off.
coherence    : FAIL if tone is cold/robotic OR it contradicts an earlier turn.
               PASS if warm and internally consistent.
```

## Against WHAT — the golden set

The golden set is [`../.claude/skills/customer-care/reference/conversation-scenarios.json`](../.claude/skills/customer-care/reference/conversation-scenarios.json)
— each case carries the expected `intent`, `handoff` payload, `worker_outcome`,
and expected `relay`. That file **is** the ground truth for these dims.

> **Ground-truth hygiene (learned the hard way):** assert on the **stable**
> field (`decision` = ESCALATE), never on a **drifting** one (e.g. "exactly 7
> days" — date-based data drifts). Let the decision be the assertion; treat the
> day count as narration. This is "thresholds absorb non-determinism."

---

## Run it — the judge prompt (paste in a fresh session)

After you capture a conversation transcript, run the judge over it:

```
Use the customer-care conversation-eval rubric in docs/02-conversation-eval.md.

Here is a transcript of a coordinator conversation:
<paste the full transcript, all turns>

Expected (from reference/conversation-scenarios.json, scenario "<id>"):
<paste that scenario's expected block>

Grade it. For EACH criterion — intent accuracy, action accuracy, decision
preserved, faithfulness, slot-filling, coherence — output PASS/FAIL plus one
sentence of evidence. End with an overall PASS/FAIL and a one-line summary.
```

Deterministic criteria the judge can also check by exact comparison; the three
subjective ones it scores against the rubric above.

---

## Glossary (interview vocabulary)

| Term | Plain meaning |
|---|---|
| **trajectory eval** | grade the path of turns, not just the last answer |
| **turn-level / session-level** | grade each turn vs grade the whole conversation |
| **ground truth / golden set** | the curated expected-behavior cases |
| **intent accuracy** | did it route to the right specialist |
| **tool-call / action accuracy** | did it call the right thing with the right args |
| **faithfulness / groundedness** | reply is backed by the source, invents nothing |
| **LLM-as-judge / model-graded / autorater** | a second LLM scores against a rubric |
| **rubric** | the written scoring criteria the judge follows |
| **task success rate** | % of conversations that achieved the customer's goal |
| **regression gate** | run the whole golden set before shipping; all-pass = safe |
| **user simulator** | an LLM playing the customer to drive many test conversations at scale |

---

## How this grows

- **M1 (now):** manual/judge eval over a handful of golden conversations.
- **Later:** a **user simulator** drives many conversations; the judge scores
  them; results become a **regression gate** in CI — the same role `adk eval`
  plays for the worker.
