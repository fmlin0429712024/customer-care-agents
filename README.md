# Customer Care Multi-Agent System

*An MVP two-agent solution (**Google ADK** + **A2A**) — prototyped as **Claude Code
skills**, then run with a full **harness & governance** layer. Implemented two
ways: **application-level** on Cloud Run, and **platform-managed** on Vertex
Agent Engine.*

> ## ▶ The point — one harness, built two ways
> The core of this repo is a side-by-side of the **same** multi-agent harness &
> governance, implemented two ways. Same agents, same policy — the only
> difference is **who provides sessions, memory, tracing & governance**:
>
> ### ① [Application-level — on Cloud Run](docs/harness-cloud-run.md) → *you build the harness*
> ### ② [Platform-managed — on Agent Engine](docs/harness-agent-platform.md) → *the platform provides it*
>
> **That comparison is the value. Everything below is the context that makes it land.**

```
   You ──chat──▶  care_agent   (coordinator · intake · long, multi-turn · :8042)
                      │
                      │   A2A  (HTTP + Agent Card — the frozen interface)
                      ▼
                 refund_agent  (worker · specialist · short, one-shot · :8043)
                      │
        order_lookup ─▶ refund_decision ─▶ fraud_detection ─▶ customer_reply
```

An **agent system**, not a single agent: a conversational **coordinator** that
takes the customer intake and, when the topic turns to a refund, delegates to an
independent **specialist worker** over the A2A protocol. This mirrors the
Gemini-Enterprise / Agentspace pattern — a front door that dispatches to
registered specialists.

Three questions an interviewer asks, three sections:

---

## 1 · The solution — *what it does*

| Agent | Role | Session shape | Job |
|-------|------|---------------|-----|
| [`customer-care-agent/`](customer-care-agent/) | **coordinator** · intake | long, multi-turn | greet, classify intent, slot-fill, **delegate** refunds |
| [`refund-agent/`](refund-agent/) | **worker** · specialist | short, one-shot | a 4-stage `SequentialAgent`: lookup → decide → fraud-screen → reply |

- **A2A is the business integration**, not glue: the coordinator sees the worker
  as a **black box** behind a frozen **Agent Card** — it sends an `order_id`, it
  gets back a decision. The two agents deploy, scale, and version independently.
- The refund policy (auto-approve / escalate / reject, fraud rules, SLA) lives in
  the worker; the coordinator owns routing and conversation.

## 2 · How it's built — *Claude Code skills → ADK*

The differentiator: **prototype fast in Claude Code, migrate verbatim to ADK.**

```
   Claude Code SKILL.md  ──(byte-identical copy)──▶  ADK agent instruction
      (rapid authoring)                                 (production runtime)
```

- **Policy lives in `SKILL.md`** and is copied **byte-identical** into the ADK
  agent. Business logic is never re-authored in Python.
- Only the **host wiring** differs per environment — tools, `output_key`,
  memory, the A2A hookup — and lives in `agent.py`, never in the skill.
- Result: the same policy runs in the Claude Code playground (design) and on ADK
  (production), so behavior is identical and the migration path is a copy, not a
  rewrite.

## 3 · How it runs — *harness & governance*

**Harness** = runtime scaffolding (sessions, state, memory, tools, observability).
**Governance** = controls (guardrails/PII, policies, audit, identity). The
cross-cutting concerns are **assigned by role**, not copied onto both agents —
which is exactly what makes the coordinator differ from the worker:

| Concern | Layer | Care (intake) | Refund (worker) | Interface form | Platform-managed? |
|---------|-------|:-------------:|:---------------:|----------------|:-----------------:|
| Observability (tracing) | harness/gov | ✅ its slice | ✅ its slice | export pipe | ✅ |
| Guardrail (PII redaction) | governance | ✅ **first line** | ◐ defense-in-depth | injected logic | ✅ |
| Memory (returning customer) | harness | ✅ | ❌ *stateless worker* | service ref | ✅ |
| Session / State (slot-filling) | harness | ✅ heavy | ◐ minimal | service ref | ✅ |
| Context management (long chat) | harness | ✅ | ❌ | cross-cutting | ◐ |
| Distributed trace across A2A | harness/gov | ✅ correlate | ✅ correlate | context propagation | ✅ |

> **Read-off:** memory and heavy state land on the **coordinator only** — the
> worker is short and stateless. That asymmetry *is* the coordinator-vs-worker
> thesis, made concrete at the deployment layer.

The same harness is implemented **two ways** — the core comparison of this repo:

| Way | Substrate | Who provides the harness | Doc |
|-----|-----------|--------------------------|-----|
| **1 · Application-level** | Cloud Run (bare compute) | **you build it** in the app | [**Harness & Governance — Cloud Run**](docs/harness-cloud-run.md) |
| **2 · Platform-managed** | Vertex Agent Engine | **the platform provides it** — you configure | [**Harness & Governance — Agent Engine**](docs/harness-agent-platform.md) |

Concepts behind it all (deployment-agnostic): [**Agent Engineering — First
Principles & the 2026 Landscape**](docs/agent-first-principles.md).

---

## Run it locally (2 terminals)

```bash
# terminal 1 — refund A2A server (start first)
cd refund-agent/adk_refund && .venv/bin/uvicorn a2a_server:a2a_app --host localhost --port 8043

# terminal 2 — care coordinator playground
cd customer-care-agent/adk_care && .venv/bin/adk web --port 8042 .
```

Then in the care dev-ui: `I want my money back` → it asks for the order →
`order 12345` → open **Events / Traces** and watch `transfer_to_agent("refund_agent")`
fire the A2A call. Setup + gotchas: [docs/03-a2a-local.md](customer-care-agent/docs/03-a2a-local.md).

Harness worked examples (self-contained, localhost):

```bash
cd customer-care-agent/adk_care
.venv/bin/python m3_memory_demo.py       # memory: recall a returning customer ACROSS sessions
.venv/bin/python session_state_demo.py   # state: slot-fill ACROSS turns, empty in a new session
```

## Status

Worker: ✅ built, traced, guarded, deployed (Cloud Run + Agent Engine). Coordinator:
✅ routing · slot-filling · A2A handoff · memory · session/state (local worked
examples). Next: context management (M4) and distributed tracing across A2A.
