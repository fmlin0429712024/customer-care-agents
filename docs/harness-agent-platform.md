# Platform-Managed Harness & Governance — Vertex Agent Engine

*The platform provides an integrated harness. Vertex Agent Engine (the managed
agent tier of the Gemini Enterprise Agent Platform) supplies sessions, tracing,
and — at the org tier — policy governance as **managed services**. You hand over
the **agent + requirements**; the platform **builds the container** and runs it.
The trade: managed does not mean zero configuration, and the integrated controls
exist only while running on the platform.*

This is **Way 2** of two. Contrast: [Way 1 — application-level on Cloud
Run](harness-cloud-run.md).

> **✅ Deployed & verified (us-central1):** the refund worker runs on Agent Engine.
> - Reasoning Engine: `projects/51058313466/locations/us-central1/reasoningEngines/1925814957014777856`
> - Verified via `stream_query`: order 67890 → full 4-stage pipeline → **APPROVE**.
> - We shipped **no Dockerfile and no serve.py** — `adk deploy agent_engine`
>   generated the container; the platform provides sessions + tracing.

```
   ┌──────────────── Vertex Agent Engine (managed runtime) ────────────────┐
   │  Managed Sessions ·  Managed Tracing → Cloud Trace  ·  [Govern tabs]   │
   │                                                                        │
   │        ┌───────────────────────────────────────────────┐             │
   │        │  refund_agent  (your agent + requirements.txt) │             │
   │        │  platform-built container · 4-stage pipeline   │             │
   │        └───────────────────────────────────────────────┘             │
   │   you deploy the AGENT; the platform packs the box + hangs the harness │
   └────────────────────────────────────────────────────────────────────────┘
```

---

## The principle

An **agent platform** is compute **plus** a managed harness. You deploy a
structured ADK agent (its code + `requirements.txt`); the platform **containerizes
it for you** and attaches sessions, tracing, and — at the org tier — governance
**around** it. The cost: those managed controls are **not portable** — leave the
platform and they're gone (that's Way 1's job).

## What actually happened (the deploy process)

```bash
# from refund-agent/adk_refund, using the venv that has the vertexai SDK
adk deploy agent_engine \
  --project=linkhealth-care-2024 --region=us-central1 \
  --display_name="Refund Agent" --otel_to_cloud \
  refund_agent
```

- `adk deploy agent_engine` reads `refund_agent/` (code + `requirements.txt` +
  `.env`), **generates a Dockerfile**, builds the image, and registers a Reasoning
  Engine. You write no container/serve code.
- The managed runtime provides **Sessions** (used by `stream_query`) and, with
  `--otel_to_cloud`, **tracing** to Cloud Trace.

**The gotcha that actually cost us (worth remembering):**

> "Platform packs the container" ≠ "platform figures out your dependencies." The
> deploy reported success, but the runtime **failed to start** — ADK 2.4.0's
> `--otel_to_cloud` telemetry imports `opentelemetry-exporter-otlp-proto-http` at
> startup, which wasn't in `requirements.txt`. **Lesson: never trust "deployed" —
> drive a real query; on failure read the ReasoningEngine logs.** Fix: add the
> OTLP/HTTP + Cloud Trace exporters to `refund_agent/requirements.txt`.

Also: managed Sessions **reject API keys** — the agent must run in **Vertex mode**
(`GOOGLE_GENAI_USE_VERTEXAI=TRUE`), auth via the runtime's service account (needs
`roles/aiplatform.user` + `roles/datastore.user`).

## Per concern — what the platform manages

| Concern | Layer | Platform service | Status here |
|---------|-------|------------------|-------------|
| **Container / packaging** | ops | `adk deploy` generates the Dockerfile; platform builds it | ✅ verified |
| **Sessions / State** | harness | managed Agent Engine Sessions | ✅ used by `stream_query` |
| **Observability** | harness/gov | managed tracing → Cloud Trace (`--otel_to_cloud`) | ✅ enabled |
| **Memory** | harness | **Memory Bank** — durable, cross-session, auto LLM extraction | ◻ not wired (gap) |
| **Guardrail / policy** | governance | **Policies** + runtime **SGP** (evaluate tool calls vs org rules) | ◻ not set up (gap) |
| **Discovery** | governance | **Agent Registry** — register, route, version | ◻ not registered (gap) |
| **Identity** | governance | IAM / service accounts, per-user (multi-tenant) | ✅ runs under the RE service account |

## The app-code delta depends on the interface form

Moving a concern from app-level to platform-managed is **not** uniform — it
depends on how the concern is exposed:

| Interface form | Concern | App-code delta |
|----------------|---------|----------------|
| **Service reference** | Session/State, Memory | swap **one line**: `InMemory… → VertexAiSessionService / VertexAiMemoryBankService` |
| **Export pipe** | Observability | a flag (`--otel_to_cloud`) — platform auto-captures; drop your OTel setup |
| **Injected logic** | Guardrail (PII) | the app **plugin does not ride along** (the platform deploys the *agent*, not your `serve.py`); its platform form is a **Policy / SGP** you configure |

> Note the guardrail point, learned concretely here: our Cloud Run guardrail was a
> `serve.py` plugin. `adk deploy agent_engine` deploys the **agent**, so that
> plugin isn't present on Agent Engine — the platform equivalent is a **Policy**,
> which lives in the org/governance tier (below).

## Gaps (honest) — what's *not* done on the platform

- **Memory Bank** not wired — the managed memory backend isn't attached yet
  (would be the `VertexAiMemoryBankService` reference).
- **Governance tier** (Policies / SGP / Agent Registry / Gateways) is the
  **console + Preview** layer of the Gemini Enterprise Agent Platform. It's
  largely portal-driven today; setting it up via CLI/Terraform is limited, and it
  postdates this author's knowledge cutoff — documented conceptually, not deployed.
- **A2A between two Agent Engines** — only the **worker** is on Agent Engine; the
  care coordinator is not (Way 2 is shown single-agent). Cross-engine A2A is the
  managed-registry analogue of Page 1's two-container A2A.

## Why the platform, at scale (the genuinely unique part)

Two agents by hand is fine (Way 1). The platform earns its place at **many**
agents, **many** users, **compliance**: it enforces governance **around** every
agent (non-bypassable, audited), keys memory + identity **per tenant**, and
provides **discovery** — things a single application **cannot provide for *other*
agents**. Those cross-agent / org-scale features are the platform's true
exclusives; single-agent harness (sessions, trace, guardrail, memory) an
application can do just as well (Way 1), only with more manual wiring.

## Governance: placement, not a pipeline

The same control can live in the app (Way 1) or on the platform (Way 2) — a
**placement** decision, not "app does / platform manages" (both *do*). When both
are present they **stack**: the platform policy is a **floor** the agent cannot go
below; the app may add **stricter** controls, never looser. Keep app-level for
**portability**; use platform-level for **org-wide enforcement**.

## Config-as-code

The core platform is **API-first** — the console is a UI over the same APIs.
Configure via the Vertex **Python SDK**, **gcloud**, or **Terraform**. Prefer
**Terraform/IaC** for governance: declarative, version-controlled, auditable —
itself good governance (and AI-assistable). The newest Preview governance features
may lag on API/IaC coverage.
