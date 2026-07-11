# Application-Level Harness & Governance — Cloud Run

*You build the harness. Cloud Run gives you **bare compute** (a container that
scales) and **nothing agent-specific** — so sessions, memory, observability, and
guardrails are all wired **in the application**, and travel with the agent
wherever it runs.*

This is **Way 1** of two. Contrast: [Way 2 — platform-managed on Agent
Engine](harness-agent-platform.md).

```
   Cloud Run service (care)        Cloud Run service (refund)
   ┌───────────────────────┐  A2A  ┌───────────────────────┐
   │  ADK agent            │◀─────▶│  ADK agent            │
   │  + harness (in app):  │       │  + harness (in app):  │
   │  trace · memory ·     │       │  trace · guardrail    │
   │  session/state        │       │                       │
   └───────────────────────┘       └───────────────────────┘
        bare compute — you bring everything above the container
```

---

## The principle

Cloud Run is a **substrate**, not an agent platform. It runs your container and
autoscales it — that's all. Every cross-cutting concern is therefore
**application-level**: it lives in your code, is deployed with the agent, and
**protects the agent everywhere** (localhost, another cloud, on-prem). The cost:
**you** are responsible for wiring, correctness, and persistence.

## The one Cloud Run gotcha: it's stateless & multi-instance

A Cloud Run container is **ephemeral** and may run as **many instances**. So
**in-memory harness state does not survive** — you must **externalize** it:

| Concern | Local (single process) | Cloud Run (stateless) → you externalize |
|---------|------------------------|------------------------------------------|
| Session / State | `InMemorySessionService` | `DatabaseSessionService` (a DB) |
| Memory | `InMemoryMemoryService` | a persistent backend (Firestore / DB) |
| Data | in-memory dict | Firestore ([03.5](../refund-agent/adk_refund/docs/03.5-firestore-data-layer.md)) |

**"Swap the backend, not the concept"** — the agent code is unchanged; only the
service *reference* points at a durable store.

## Per concern — how it's wired (with file pointers)

| Concern | Layer | How (application-level) | Where |
|---------|-------|-------------------------|-------|
| **Observability** | harness/gov | OTel tracer + exporters (dual: Cloud Trace + LangSmith), set at the serve layer | [`serve_dual_trace.py`](../refund-agent/adk_refund/serve_dual_trace.py) · [doc 01](../refund-agent/adk_refund/docs/01-observability-tracing.md) |
| **Guardrail (PII)** | governance | an ADK **Plugin** (a `before_model` hook) redacts PII before every model call; registered via `extra_plugins` | [`guardrails.py`](../refund-agent/adk_refund/guardrails.py) · [doc 02](../refund-agent/adk_refund/docs/02-governance-pii-guardrail.md) |
| **Memory** | harness | `MemoryService` + a `load_memory` tool + `add_session_to_memory` | [`m3_memory_demo.py`](../customer-care-agent/adk_care/m3_memory_demo.py) |
| **Session / State** | harness | `SessionService` + tools writing `tool_context.state` (slot-filling) | [`session_state_demo.py`](../customer-care-agent/adk_care/session_state_demo.py) |
| **Deploy** | ops | container → Cloud Run (`us-central1`), reuse a dev service account | [doc 03](../refund-agent/adk_refund/docs/03-cloud-run-deployment.md) |

The pattern is consistent: **governance/harness is injected at the wiring layer
(`serve_*.py`, `agent.py`), never in `SKILL.md`.** Policy stays byte-identical;
operability is bolted on around it.

## Two agents, assigned by role

Because the two agents are **independent Cloud Run services**, each carries only
what its role needs:

- **care (intake):** trace · guardrail (first line — customer PII enters here) ·
  **memory** · heavy **session/state**.
- **refund (worker):** trace · guardrail (defense-in-depth on what crosses A2A).
  **No memory, minimal state** — it is short and stateless.

## The cross-agent piece: distributed tracing (planned)

One request spans `care → A2A → refund`. To see it as **one end-to-end trace**,
the **trace context must propagate across the A2A call** so both services share a
trace ID. This is the one concern that needs coordination *between* the two apps —
not present in a single-agent setup.

## What this way demonstrates

You can see exactly **what an agent platform provides** by listing everything you
had to build here yourself: the session store, the memory backend, the trace
export, the guardrail plugin, and the persistence to survive a stateless
substrate. That list *is* the harness — and [Way 2](harness-agent-platform.md)
hands most of it to the platform.
