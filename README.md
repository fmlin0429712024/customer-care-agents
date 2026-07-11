# Customer Care Agents — two ADK agents wired over A2A (runs 100% local)

A conversational **coordinator** that delegates to a specialist **refund worker**
over the **A2A protocol**. Both agents are authored as Claude-Code **SKILLs**,
migrated **verbatim** to **Google ADK**, and run **entirely on localhost** — no
cloud required.

```
   You ──chat──▶  care_agent   (coordinator · LLM-routed · :8042 dev-ui)
                      │
                      │   A2A  (HTTP + Agent Card, the frozen interface)
                      ▼
                 refund_agent  (worker · SequentialAgent · :8043 A2A server)
                      │
        order_lookup ─▶ refund_decision ─▶ fraud_detection ─▶ customer_reply
```

The coordinator sees the worker as a **black box**: it sends an `order_id`, it
gets back a decision. The worker's 4-stage pipeline is hidden behind the A2A
Agent Card.

---

## The recipe — SKILLs → ADK → A2A → localhost

### 1 · Refund Agent (worker) — the A2A **server**

| Layer | What | Where |
|-------|------|-------|
| **Policy** | 8 `SKILL.md` files (Claude Code), copied **byte-identical** | [`refund_agent/skills/customer-refund/`](refund-agent/adk_refund/refund_agent/skills/customer-refund/) |
| **ADK agent** | `SequentialAgent` = 4 sub-agents; `tools.py` (Firestore) | [`refund_agent/agent.py`](refund-agent/adk_refund/refund_agent/agent.py) |
| **Expose over A2A** | `a2a_app = to_a2a(root_agent, port=8043)` — one wrapper, agent.py untouched | [`a2a_server.py`](refund-agent/adk_refund/a2a_server.py) |

```bash
cd refund-agent/adk_refund
.venv/bin/uvicorn a2a_server:a2a_app --host localhost --port 8043
# → Agent Card auto-generated at  http://localhost:8043/.well-known/agent-card.json
```

### 2 · Care Agent (coordinator) — the A2A **client**

| Layer | What | Where |
|-------|------|-------|
| **Policy** | `customer-care/SKILL.md` (routing · slot-filling), copied verbatim | [`care_agent/skills/customer-care/`](customer-care-agent/adk_care/care_agent/skills/customer-care/) |
| **ADK agent** | LLM `Agent`; consumes the worker as a sub-agent | [`care_agent/agent.py`](customer-care-agent/adk_care/care_agent/agent.py) |
| **Call over A2A** | `RemoteA2aAgent(agent_card="http://localhost:8043/.well-known/agent-card.json")` | same file |

```bash
cd customer-care-agent/adk_care
.venv/bin/adk web --port 8042 .
# → open http://127.0.0.1:8042 , pick care_agent
```

### 3 · Run the whole system (2 terminals)

```bash
# terminal 1 — refund A2A server (start first)
cd refund-agent/adk_refund && .venv/bin/uvicorn a2a_server:a2a_app --host localhost --port 8043

# terminal 2 — care coordinator playground
cd customer-care-agent/adk_care && .venv/bin/adk web --port 8042 .
```

Then in the care dev-ui: `I want my money back` → it asks for the order → `order 12345`
→ open the **Events / Traces** tab and watch **`transfer_to_agent("refund_agent")`**
fire the A2A call. The remote worker runs all 4 stages and the decision comes back.

> **One-time setup** if starting fresh: each agent gets its own venv
> (`python3 -m venv .venv && .venv/bin/pip install -e .`) plus the A2A extras
> `pip install "google-adk[a2a]" "a2a-sdk[http-server]"`. Full runbook:
> [docs/03-a2a-local.md](customer-care-agent/docs/03-a2a-local.md).

---

## The ideas worth knowing (the interview-relevant bones)

- **SKILL.md = policy, verbatim.** Identical bytes Claude Code → ADK; only the
  *host wiring* (`agent.py`: tools, `output_key`, the A2A hookup) differs per
  environment. Never re-author policy in Python.
- **A2A = agent → agent** over a **frozen interface** (the Agent Card). Contrast
  **MCP = agent → tools**. In-process `sub_agent` is the same handoff *co-located*;
  A2A is the same handoff *over the network*. Choice is **topology, not quality**.
- **`to_a2a()` does the protocol for you** — auto-generates the Agent Card, the
  executor, the task store, the routes. You write one line.
- **Local = files + localhost.** SQLite/Firestore for data, `session.db` for
  sessions, HTTP over `127.0.0.1` for A2A. The cloud swaps backends, not the code.

## The two agents

| Agent | Role | Session | Status |
|-------|------|---------|--------|
| [`refund-agent/`](refund-agent/) | worker · specialist | short, one-shot | ✅ done · also deployed to Agent Engine |
| [`customer-care-agent/`](customer-care-agent/) | coordinator · front desk | long, multi-turn | ✅ routing · slot-filling · **A2A handoff** |

## Docs

| # | Doc | Covers |
|---|-----|--------|
| 01 | [Coordinator design](customer-care-agent/docs/01-coordinator-design.md) | routing · handoff contract · how it becomes A2A |
| 02 | [Conversation eval](customer-care-agent/docs/02-conversation-eval.md) | trajectory eval · LLM-as-judge · rubric |
| 03 | [**A2A, local, step by step**](customer-care-agent/docs/03-a2a-local.md) | expose (`to_a2a`) · consume (`RemoteA2aAgent`) · run · gotchas |

Worker deep-dives (tracing · guardrail · Cloud Run · Firestore · eval · Agent Engine):
[`refund-agent/adk_refund/docs/`](refund-agent/adk_refund/docs/).

## What's next

Memory (remember the returning customer) and context management (long
conversations) — the parts where the coordinator truly diverges from the worker.
