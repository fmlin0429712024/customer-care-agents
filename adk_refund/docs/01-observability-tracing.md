# 01 — Observability: Tracing (Cloud Trace + LangSmith)

**Status: ✅ Done — first milestone.** The local ADK agent emits OpenTelemetry
traces that we view in **Google Cloud Trace** and **LangSmith**, side by side,
with **zero changes to business code**.

---

## What we set up

A single refund run produces one trace that fans out to two backends:

```
agent.py / tools.py / SKILL.md        ← business logic — ZERO tracing code
        │  ADK library emits OTel spans (call_llm, execute_tool, invoke_agent…)
        ▼
  global OpenTelemetry TracerProvider  ← the only thing we wire
        │
   ┌────┴─────────────┐
   ▼                  ▼
Cloud Trace        LangSmith
(GCP console)      (smith.langchain.com)
```

Key point: **observability is decoupled**. The instrumentation (where spans are
created) lives inside the `google-adk` library, not our code. We only choose
*where the data goes*, in a wiring layer — never in `agent.py` or any SKILL.md.

---

## Prerequisites (one-time)

```bash
# exporters (into the venv)
pip install opentelemetry-exporter-gcp-trace opentelemetry-exporter-otlp-proto-http

# GCP: project + auth + Cloud Trace API (already done for linkhealth-care-2024)
gcloud config set project linkhealth-care-2024
gcloud auth application-default login          # once; ADC used by the exporter
gcloud services enable cloudtrace.googleapis.com

# LangSmith: free account → API key → store it git-ignored
#   file: adk_refund/.env.local
#   LANGSMITH_API_KEY=lsv2_...
#   LANGSMITH_PROJECT=refund-agent
```

---

## How to run

### Cloud Trace only (simplest)

```bash
cd adk_refund && source venv/bin/activate
export GOOGLE_CLOUD_PROJECT=linkhealth-care-2024
adk web --trace_to_cloud --port 8001
```

> `--otel_to_cloud` also exports **logs**, but needs
> `opentelemetry-exporter-gcp-logging`. Use `--trace_to_cloud` for traces only.

### Dual export — Cloud Trace **and** LangSmith

```bash
cd adk_refund && source venv/bin/activate
set -a; source .env.local; set +a               # loads LANGSMITH_API_KEY
export GOOGLE_CLOUD_PROJECT=linkhealth-care-2024
python serve_dual_trace.py                       # http://127.0.0.1:8001
```

`serve_dual_trace.py` is pure host wiring: it attaches two exporters to the
global tracer provider, then serves the same agent. It imports **no** business
module.

Generate a trace by sending a refund in the playground UI, or via REST:

```bash
curl -s -X POST http://127.0.0.1:8001/apps/refund_agent/users/u1/sessions/s1 -d '{}'
curl -s -X POST http://127.0.0.1:8001/run -H 'Content-Type: application/json' -d '{
  "app_name":"refund_agent","user_id":"u1","session_id":"s1",
  "new_message":{"role":"user","parts":[{"text":"Process refund for order 12345"}]}}'
```

---

## Where to view

| Backend | URL | Note |
|---------|-----|------|
| Cloud Trace | https://console.cloud.google.com/traces/list?project=linkhealth-care-2024 | 2–5 min indexing latency |
| LangSmith | https://smith.langchain.com → project **refund-agent** | project auto-created on first export |

Both show the same 4-stage pipeline. What differs:

| | Cloud Trace | LangSmith |
|---|---|---|
| Layout | time **waterfall** (latency focus) | run **tree** (structure focus) |
| Span typing | one GenAI span kind | auto-typed **tool / llm / chain** |
| Prompt / response | in span attributes (expand) | side-by-side **Input / Output** |
| Tokens / cost | GenAI token summary | per-step tokens + cost estimate |
| Higher-level | none (raw observability) | datasets / eval / annotation |

Both capture the LLM layer (prompt, model, tokens, tool calls) via the OTel
GenAI semantic conventions — not just system-level metrics.

---

## Controlling what gets captured (granularity)

OTel does **not** capture everything — only where ADK created a span. Knobs:

| Knob | Controls | Where |
|------|----------|-------|
| Sampling | fraction of traces kept | `TracerProvider(sampler=…)` in the wiring |
| Span filter | which spans export | custom `SpanProcessor` in the wiring |
| **Content capture** | record prompt/response **text** | env `ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS` |
| Extra detail | trace your own function internals | add a span in your code (opt-in) |

`ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS` defaults **on** locally (you see the full
SKILL.md prompt in the span) but ADK's deploy path defaults it **off** for
privacy. Everything except "extra detail" stays in the wiring layer — no
business-code change.

---

## The one concept to remember

> Decoupled ≠ "not code". Decoupled = **the business code doesn't know it exists**.
> `agent.py` has zero OpenTelemetry lines, yet every run is fully traced —
> because the framework (ADK) is already instrumented and we only wire the
> destinations.
