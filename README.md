# Customer Care Multi-Agent System

A two-agent customer-service system built with **Google ADK** and **A2A**: a
conversational **coordinator** takes the customer intake and, when the topic turns
to a refund, delegates to an independent **specialist worker** over A2A. Both
agents were prototyped as **Claude Code skills** and migrated **verbatim** into
ADK — policy is authored once, never rewritten in Python.

The engineering worth reviewing is three deep-dive pages, reached from the
sections below:

- **How you run it — the same harness, built two ways:** ① [Application-level · Cloud Run](docs/harness-cloud-run.md) · ② [Platform-managed · Agent Engine](docs/harness-agent-platform.md)
- **How you know it's correct:** ③ [The evaluation loop](docs/eval-loop.md)

## 1. What it does

```mermaid
flowchart TB
    user(["Customer"])

    subgraph CARE["care_agent — coordinator · intake · long, multi-turn"]
        route["classify intent · slot-fill order_id"]
    end

    subgraph REFUND["refund_agent — worker · specialist · short, one-shot"]
        direction LR
        s1["order_lookup"] --> s2["refund_decision"] --> s3["fraud_detection"] --> s4["customer_reply"]
    end

    user -->|"chat"| CARE
    CARE ==>|"A2A · Agent Card — frozen interface"| REFUND
    REFUND -->|"decision + ticket"| CARE
    CARE -->|"reply"| user

    linkStyle 4 stroke:#d81b60,stroke-width:3px
```

The coordinator owns the long conversation (intent, slot-filling, customer
context). The worker is a stateless four-stage `SequentialAgent`. The **A2A hop**
(bold) is a frozen interface: the coordinator sends an `order_id`, the worker
returns a decision, and the pipeline stays hidden behind it.

| Agent | Role | Session shape | Job |
|-------|------|---------------|-----|
| [`customer-care-agent/`](customer-care-agent/) | **coordinator** · intake | long, multi-turn | greet, classify intent, slot-fill, **delegate** refunds |
| [`refund-agent/`](refund-agent/) | **worker** · specialist | short, one-shot | `order_lookup → refund_decision → fraud_detection → customer_reply` |

- **A2A is the integration, not glue.** The coordinator sees the worker as a black
  box behind an Agent Card. The two agents deploy, scale, and version independently.
- **The coordinator never decides refunds.** Policy (approve / escalate / reject,
  fraud rules, SLA) lives in the worker; the coordinator owns routing and conversation.

## 2. How it's built — Claude Code skills → ADK

```
   Claude Code SKILL.md  ──(byte-identical copy)──▶  ADK agent instruction
      (rapid authoring)                                 (production runtime)
```

- **Policy lives in `SKILL.md`** and is copied byte-identical into the ADK agent.
  Business logic is never re-authored in Python.
- Only the **host wiring** differs per environment — tools, `output_key`, memory,
  the A2A hookup — and lives in `agent.py`, never in the skill.
- The same policy runs in the Claude Code playground (design) and on ADK
  (production), so the migration path is a copy, not a rewrite.

## 3. How it runs — harness & governance

**Harness** is the runtime scaffolding (sessions, state, memory, tools, tracing);
**governance** is the controls (PII guardrails, policies, audit, identity). These
concerns are **assigned by role**, not copied onto both agents — which is what
makes the coordinator differ from the worker:

| Concern | Care (intake) | Refund (worker) | Interface form |
|---------|:-------------:|:---------------:|----------------|
| Tracing | ✅ its slice | ✅ its slice | export pipe |
| PII guardrail | ✅ **first line** | ◐ defense-in-depth | injected logic |
| Memory (returning customer) | ✅ | ❌ *stateless worker* | service ref |
| Session / state (slot-filling) | ✅ heavy | ◐ minimal | service ref |

The read-off: **memory and heavy state land on the coordinator only** — the worker
is short and stateless. That asymmetry *is* the coordinator-vs-worker split, made
concrete at the deployment layer.

That same harness — same policy — is then built **two ways**. Both are **deployed
and verified**; the two pages are the deep dive:

| | ① [**Cloud Run**](docs/harness-cloud-run.md) (application-level) | ② [**Agent Engine**](docs/harness-agent-platform.md) (platform-managed) |
|---|---|---|
| Who provides the harness | **you build it** in the app | **the platform provides it** |
| Container · serve · tracing | you write them (`Dockerfile`, `serve.py`, OTel) | `adk deploy` generates them; tracing is a flag |
| Trade-off | runs **anywhere** (portable) | **org-wide** enforcement (platform-only) |
| Status | ✅ 2 services, real A2A / HTTPS | ✅ `stream_query` verified |

For a **single agent**, the app can do everything the platform does — Cloud Run is
the more fundamental layer. The platform's real exclusives are all **cross-agent /
org-scale**: registry and discovery, org-wide non-bypassable governance,
multi-tenant identity, cross-agent audit — things one app cannot provide *for
other agents*.

## 4. How it's tested — the evaluation loop

*How do you know it's correct?* The [**evaluation loop**](docs/eval-loop.md) is a
localhost QA gate that runs end-to-end across both agents and pinpoints **which
agent** failed, on **two axes**: **trajectory** (care — did it route without
self-deciding?) and **outcome** (refund — the right decision *and* an honest reply?).

The idea worth the click: **a golden-set match is an assertion, not a judge.** An
**LLM-as-judge** is needed only where free text can hallucinate — a reply that
promises an approval the customer never got. The suite proves it: one case flips
**PASS → FAIL** only once the real model (`gemini-2.5-flash`) is switched on, catching
what the offline check misses.

The loop has **two jobs**: a pre-deploy **regression gate** and a post-deploy
**data flywheel** (real traffic → human-in-the-loop → new golden → better agents).

## 5. Repository map

```text
customer-care-agent/   coordinator: conversation, state, memory, A2A client
refund-agent/          specialist worker: policy, fraud screening, A2A server
docs/                  the three deep dives + deployment notes
eval/                  end-to-end dataset, trajectories, judge, results
```

## 6. Run locally

```bash
# terminal 1 — refund A2A server (start first; care needs its Agent Card)
cd refund-agent/adk_refund
.venv/bin/uvicorn a2a_server:a2a_app --host localhost --port 8043

# terminal 2 — care coordinator playground
cd customer-care-agent/adk_care
.venv/bin/adk web --port 8042 .
```

In the coordinator UI: `I want my money back` → give `order 67890` → open
**Events / Traces** and watch `transfer_to_agent("refund_agent")` fire the A2A
call. The evaluation suite runs standalone:

```bash
python3 eval/run_eval.py            # offline; add --live-judge for the real model
```

## 7. Status

Worker: ✅ built, traced, guarded, deployed (Cloud Run + Agent Engine).
Coordinator: ✅ routing · slot-filling · A2A handoff · memory · session/state.
Evaluation: ✅ end-to-end loop, two axes, golden + LLM-as-judge.
Next: live judge + human-in-the-loop, context management for long conversations,
and distributed tracing across the A2A hop.
