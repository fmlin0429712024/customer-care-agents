# Platform-Managed Harness & Governance — Vertex Agent Engine

*The platform provides the harness. Vertex Agent Engine (the managed agent tier
of the Gemini Enterprise Agent Platform) supplies sessions, memory, tracing, and
policy governance as **managed services** — so you **configure**, you don't
re-code. The trade: it exists **only while running on the platform**.*

This is **Way 2** of two. Contrast: [Way 1 — application-level on Cloud
Run](harness-cloud-run.md).

```
   ┌──────────────────────── Agent Engine (managed) ─────────────────────────┐
   │  Managed Sessions · Memory Bank · Tracing · Policies/SGP · Registry      │
   │  ┌────────────────┐   A2A/registry   ┌────────────────┐                  │
   │  │  care agent    │◀────────────────▶│  refund agent  │                  │
   │  └────────────────┘                  └────────────────┘                  │
   │     you deploy the agent; the platform hangs the harness around it       │
   └──────────────────────────────────────────────────────────────────────────┘
```

---

## The principle

An **agent platform** is compute **plus** a managed harness. You deploy a
structured ADK agent; the platform attaches sessions, memory, tracing, and
governance **around** it — centrally, enforced, and audited across *every* agent.
The cost: those controls are **not portable** — leave the platform and they're
gone (that's Way 1's job).

## The app-code delta depends on the interface form

Moving a concern from app-level to platform-managed is **not** uniform. What
changes in your code depends on how the concern is exposed:

| Interface form | Concern | App-code delta when moving to platform |
|----------------|---------|-----------------------------------------|
| **Service reference** | Session/State, Memory | swap **one line**: `InMemory… → VertexAiSessionService / VertexAiMemoryBankService`; the tool + save/load wiring stays |
| **Export pipe** | Observability | repoint the exporter, or drop it and let the platform auto-capture (a flag) |
| **Injected logic** | Guardrail (PII) | **delete** the plugin; reconfigure as a platform **Policy / SGP** — the logic leaves your codebase |

> Memory/state are the cleanest ("point the reference at the managed backend");
> the guardrail is the one you can most fully **remove** from app code, because a
> policy engine replaces it.

## Per concern — what the platform manages

| Concern | Layer | Platform service | App does |
|---------|-------|------------------|----------|
| **Sessions / State** | harness | managed Agent Engine Sessions (multi-day) | point at the service |
| **Memory** | harness | **Memory Bank** — durable, cross-session, with automatic LLM extraction/consolidation | point at the service + keep the memory tool |
| **Observability** | harness/gov | managed tracing, aggregated across agents | enable (config) |
| **Guardrail / policy** | governance | **Policies** + runtime **SGP** (evaluates each tool call vs intent & org rules) | configure a policy |
| **Discovery** | governance | **Agent Registry** — register, route, version | register the agent |
| **Tool connectivity** | governance | **Gateways** — controlled agent↔tool egress | declare tools |
| **Identity** | governance | IAM / service accounts, per-user (multi-tenant) | run under a service account |

Status in this repo: the worker is **deployed to Agent Engine** ([doc
05](../refund-agent/adk_refund/docs/05-agent-engine-deployment.md)); the managed
memory/sessions/policy wiring is the platform-side counterpart to the local
worked examples, configured rather than coded.

## Why the platform, at scale

Two independent agents is manageable by hand (Way 1). At **many** agents,
**many** users, and **compliance** obligations, the platform earns its place: it
enforces governance **around** every agent (non-bypassable, audited), keys memory
and identity **per tenant**, and provides **discovery** — things a single
application cannot provide for *other* agents.

## Governance: placement, not a pipeline

The same control can live in the app (Way 1) or on the platform (Way 2) — it's a
**placement** decision, not "app does / platform manages" (both *do*). When both
are present they **stack**: the platform policy is a **floor** the agent cannot
go below; the app may add **stricter** controls, never looser. Keep app-level for
**portability**; use platform-level for **org-wide enforcement**.

## Config-as-code

Everything here is **API-first** — the console is a UI over the same APIs.
Configure via the Vertex **Python SDK**, **gcloud**, or **Terraform**. Prefer
**Terraform/IaC** for governance: declarative, version-controlled, auditable —
which is itself good governance (and AI-assistable).
