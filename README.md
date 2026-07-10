# Customer Care Agents — an agent-systems engineering showcase

> Two agents built to practice the **hard parts** of agentic engineering:
> multi-agent orchestration, agent-to-agent handoff (**A2A**), session & state,
> long-term memory, context management, governance, evaluation, and deployment
> on Google's agent stack.

**This is a concepts showcase, not a business demo.** The customer-service
domain is deliberately kept trivial — a front desk that routes to a specialist.
The engineering, not the business logic, is the point. (Complex-domain modeling
is demonstrated in my other projects.)

---

## Architecture — a coordinator and a worker

Two agents, developed side by side, that compose like functions: from the
outside, the whole refund worker is **one black box** with one input and one
output.

```
                  ┌──────────────────────────────┐
   customer ⇄     │   customer-care-agent         │   the COORDINATOR
                  │   · conversational front desk │   · long, multi-turn session
                  │   · understands intent        │   · owns memory + context
                  │   · routes & holds the convo  │
                  └───────────────┬──────────────┘
                                  │  handoff contract
                                  │  { order_id } → { decision, ticket }
                                  ▼
                  ┌──────────────────────────────┐
                  │   refund-agent (worker)       │   the WORKER  ✅ built
                  │   · one job, ~30s, then done  │   · SequentialAgent, 4 stages
                  │   · black box to the caller   │   · deployed to Agent Engine
                  └──────────────────────────────┘
```

The coordinator can call the worker **in-process** (ADK `sub_agents` / `AgentTool`)
or, once each is deployed independently, **over the A2A protocol** — the same
handoff contract, moved onto the network with real identity and auth. This is
deliberately the shape of **Gemini Enterprise / Agentspace**: a conversational
front door that dispatches to registered specialist agents.

---

## Concepts demonstrated — the point of this repo

| Concept | Where it lives | Learned as behavior (Claude Code) or mechanism (ADK / platform) | Status |
|---|---|---|---|
| **Orchestration — fixed (workflow)** | worker `SequentialAgent` | mechanism | ✅ done |
| **Orchestration — dynamic (LLM-routed)** | coordinator | behavior → mechanism | 🟡 M1 designed |
| **Multi-agent handoff contract** | coordinator ↔ worker | behavior → mechanism | 🟡 M1 designed |
| **Tool use / function calling** | worker `tools.py` (SQLite) | mechanism | ✅ done |
| **Session & state** | coordinator | mechanism (hidden in Claude Code) | ⬜ M3 (ADK) |
| **Long-term memory** | coordinator (Memory Bank) | mechanism | ⬜ M3 (ADK) |
| **Context management** (long chats) | coordinator | mechanism | ⬜ M4 (ADK) |
| **A2A — remote agent-to-agent call** | coordinator → worker | mechanism | ⬜ M5 |
| **Identity & security boundary** | A2A layer | mechanism | ⬜ M5 |
| **Observability — tracing** | worker (OTel → Cloud Trace + LangSmith) | mechanism | ✅ done |
| **Governance — PII guardrail** | worker (ADK Plugin) | mechanism | ✅ done |
| **Evaluation — regression gate** | worker (`adk eval`, golden set) | mechanism | ✅ done |
| **Deployment tiers** | worker (local → Cloud Run → Agent Engine) | mechanism | ✅ done |
| **Register to Gemini Enterprise** | both | mechanism | ⬜ M6 |

Two agents are enough to practice all of this — the value is depth per concept,
not sprawling to many specialists.

---

## The two agents

| Agent | Role | Session | The hard parts it carries | Status |
|---|---|---|---|---|
| [`refund-agent/`](refund-agent/) | **worker** — specialist | short, one-shot | tools, tracing, guardrail, eval, deploy | ✅ done (on Agent Engine) |
| [`customer-care-agent/`](customer-care-agent/) | **coordinator** — front desk | long, multi-turn | routing, memory, context, A2A | 🟡 building (M1) |

---

## Roadmap (the coordinator's learning arc)

| # | Milestone | The concept it teaches |
|---|-----------|------------------------|
| **M1** | LLM-routed orchestration + handoff contract (design) | dynamic routing, black-box handoff |
| **M2** | Minimal ADK coordinator → worker as in-process `sub_agent` | multi-agent composition |
| **M3** | Memory Bank | long-term memory, session & state |
| **M4** | Context management | windowing, summarization, retrieval |
| **M5** | Split deployments + remote **A2A** call | agent interop, identity, security |
| **M6** | Register to Gemini Enterprise / Agentspace | the enterprise agent surface |

**Two learning tracks:** *behavior* is prototyped fast and locally in Claude Code
(routing, persona, the contract's shape); the *mechanisms* that Claude Code hides
— session, state, memory, context, identity — are learned explicitly on **Google
ADK and the Gemini Enterprise Agent Platform**.

---

## Docs

Each milestone gets one page.

**Coordinator** — [`customer-care-agent/docs/`](customer-care-agent/docs/)

| # | Doc | Covers |
|---|-----|--------|
| 01 | [Coordinator design & handoff contract](customer-care-agent/docs/01-coordinator-design.md) | LLM routing, the handoff contract, and how it becomes A2A |

**Worker** — [`refund-agent/adk_refund/docs/`](refund-agent/adk_refund/docs/) (built series)

| # | Doc | Covers |
|---|-----|--------|
| 01 | [Observability: tracing](refund-agent/adk_refund/docs/01-observability-tracing.md) | OTel → Cloud Trace + LangSmith, dual export |
| 02 | [Governance: PII guardrail](refund-agent/adk_refund/docs/02-governance-pii-guardrail.md) | ADK Plugin redaction, managed vs custom |
| 03 | [Deployment: Cloud Run](refund-agent/adk_refund/docs/03-cloud-run-deployment.md) | single-region deploy, service account |
| 03.5 | [Data layer: SQLite → Firestore](refund-agent/adk_refund/docs/03.5-firestore-data-layer.md) | swap storage, agent unchanged |
| 04 | [Evaluation: adk eval](refund-agent/adk_refund/docs/04-evaluation-adk-eval.md) | offline regression gate |
| 05 | [Deployment: Agent Engine](refund-agent/adk_refund/docs/05-agent-engine-deployment.md) | managed agent tier, Vertex auth |

---

## Repo structure

```
customer-care-agents/
├── README.md                         ← you are here (the front door)
├── CLAUDE.md                         ← overview + roadmap (for AI assistants)
├── customer-care-agent/              ← COORDINATOR (building)
│   ├── README.md
│   └── docs/                         ← design & milestone docs
├── refund-agent/                     ← WORKER (done, deployed)
│   ├── adk_refund/                   ← the ADK agent + docs series
│   └── .claude/skills/customer-refund/
└── .claude/skills/customer-care/     ← coordinator routing skill (M1 skeleton)
```

---

**Status:** worker done & deployed to Agent Engine · coordinator at M1 (design).
**Stack:** Google ADK · Vertex AI / Agent Engine · A2A · Claude Code (prototyping).
