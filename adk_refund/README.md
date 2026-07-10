# Customer Refund Agent — Google ADK

A textbook-layout [Agent Development Kit](https://adk.dev) agent that processes
customer refund requests. It is a four-stage `SequentialAgent` pipeline built on
a clean split:

- **Policy lives in `SKILL.md`.** Each stage loads the verbatim `SKILL.md`
  files that Claude Code produced, bundled under `refund_agent/skills/`. They
  are byte-for-byte identical to `.claude/skills/customer-refund/`, proving a
  Claude-Code skill deploys to ADK unchanged. Change policy → edit the SKILL.md.
- **Data access lives in `tools.py`.** Deterministic operations (order lookup,
  refund history, ticket creation) are ADK `FunctionTools` backed by SQLite, so
  the LLM never guesses order data, date math, or ticket numbers.

## Learning roadmap — local ADK → Gemini Enterprise Agent Platform

The goal is to experience the whole pipeline, one solid step at a time. CLI
where possible (assistant-driven); portal only for viewing / enterprise setup.

| # | Milestone | How | Status |
|---|-----------|-----|--------|
| 0 | Local textbook agent + playground | `adk web` | ✅ done |
| 1 | **Observability — tracing** | Cloud Trace + LangSmith, dual export | ✅ **done** 🎉 |
| — | Governance — PII guardrail | ADK Plugin, redaction (local) | ✅ done |
| 2 | **Deploy to Cloud Run** (single region `us-central1`) | container + service account + secrets | ✅ **done** 🎉 [live](https://refund-agent-xwbl4hgnja-uc.a.run.app) |
| 2.5 | Data layer: SQLite → Firestore | swap `tools.py` internals, agent unchanged | ✅ **done** |
| 3 | Deploy to Agent Engine (managed agent tier) | `adk deploy agent_engine` (Vertex backend) | ⬜ |
| 4 | **Evaluation** | `adk eval` — golden set, offline regression gate | ✅ **done** (4/4 pass) |
| 5 | Managed Sessions / Memory | swap InMemory for platform-managed state | ⬜ |
| 6 | Governance (managed) | Model Armor / enterprise IAM / quotas (portal) | ⬜ |
| 7 | Gemini Enterprise surface | register the agent to Agentspace (portal) | ⬜ |

Tiers: **local → Cloud Run** (managed infra + scaling) **→ Agent Engine** (managed agent services). Multi-region + load balancer is concept-only.

### Docs (growing series in [`docs/`](docs/))

| # | Doc | Covers |
|---|-----|--------|
| 01 | [Observability: Tracing](docs/01-observability-tracing.md) | Cloud Trace + LangSmith, dual export, granularity knobs |
| 02 | [Governance: PII Redaction Guardrail](docs/02-governance-pii-guardrail.md) | ADK Plugin guardrail, redaction vs tokenization, managed vs custom |
| 03 | [Deployment: Cloud Run](docs/03-cloud-run-deployment.md) ✅ | single-region deploy, container vs runtime config, service account |
| 03.5 | [Data layer: SQLite → Firestore](docs/03.5-firestore-data-layer.md) ✅ | swap storage, touch one file; persistent + cross-instance |
| 04 | [Evaluation: adk eval](docs/04-evaluation-adk-eval.md) ✅ | offline regression gate; thresholds absorb LLM non-determinism |

> **Eval in one line:** `adk eval` is essentially **regression testing for CI/CD** —
> run the whole golden set before every deploy; all-pass = safe to ship. It's an
> ADK/offline feature, nothing to do with the Gemini Enterprise platform.

Each milestone gets one page.

## Layout

```
adk_refund/                        ← run `adk web` here
└── refund_agent/                  ← agent package
    ├── __init__.py                ← from . import agent
    ├── agent.py                   ← defines root_agent (the pipeline)
    ├── tools.py                   ← SQLite-backed FunctionTools (data access)
    ├── .env                       ← GOOGLE_API_KEY, GOOGLE_GENAI_USE_VERTEXAI
    ├── data/refund.db             ← generated on first run (git-ignored)
    └── skills/customer-refund/    ← verbatim hard copy of the Claude-Code skill
        ├── SKILL.md               ← orchestrator
        ├── order-lookup/SKILL.md
        ├── refund-policy/SKILL.md
        ├── refund-decision/SKILL.md
        ├── fraud-detection/SKILL.md
        ├── escalation-rules/SKILL.md
        ├── escalation-workflow/SKILL.md
        ├── customer-communication/SKILL.md
        └── reference/
            ├── orders.json
            └── test-scenarios.json
```

## Pipeline

```
order_lookup → refund_decision → fraud_detection → customer_communication
```

Each sub-agent writes its result to session state (`output_key`); the next
stage reads it. Stages call tools where the work is deterministic:

| Stage | Tool | Purpose |
|-------|------|---------|
| order_lookup | `lookup_order(order_id)` | Read the order record + compute days since delivery |
| fraud_detection | `get_refund_history(customer_id)` | Count refunds in trailing 30 days |
| customer_communication | `create_escalation_ticket(...)` | Mint a real ticket ID + SLA on escalation |

The SQLite database is seeded on first use from the bundled
`reference/orders.json`. In production you swap this layer for Cloud SQL /
Firestore without touching the agents or the SKILL.md. Point `REFUND_DB_PATH`
at a writable location (e.g. `/tmp/refund.db`) on read-only deploy targets.

## Run the playground

```bash
cd adk_refund
source venv/bin/activate       # or: pip install -e .
adk web
```

Open the printed URL, pick **refund_agent**, and type e.g.:

```
Process refund for order 67890
```

Terminal alternative:

```bash
adk run refund_agent
```

**With tracing** (Cloud Trace + LangSmith, dual export):

```bash
set -a; source .env.local; set +a               # LangSmith key
export GOOGLE_CLOUD_PROJECT=linkhealth-care-2024
python serve_dual_trace.py                       # http://127.0.0.1:8001
```

See [docs/01 — Observability: Tracing](docs/01-observability-tracing.md) for the full setup, backends, and granularity knobs.

## Test orders

| Order | Amount | Status | Days since delivery | Expected |
|-------|--------|--------|---------------------|----------|
| 67890 | $49 | delivered | 2 | APPROVE — AUTO_APPROVED |
| 12345 | $99 | delivered | 7 | ESCALATE — PAST_REFUND_WINDOW |
| 11111 | $29 | in_transit | — | ESCALATE — IN_TRANSIT |
| 99999 | — | not found | — | REJECT — ORDER_NOT_FOUND |

## Configuration

`refund_agent/.env` (read by ADK):

```
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_API_KEY=<your AI Studio key>
```

To run on Vertex AI instead, set `GOOGLE_GENAI_USE_VERTEXAI=TRUE` with
`GOOGLE_CLOUD_PROJECT` / `GOOGLE_CLOUD_LOCATION` and authenticate via
`gcloud auth application-default login`.

## Changing policy

Edit the relevant `SKILL.md` — never `agent.py`. The pipeline reads the files
at runtime, so policy changes take effect on the next run with no code change.
