# 02 — Governance: PII Redaction Guardrail

**Status: ✅ Done — second milestone (local governance preview).** Customer
messages that contain PII (SSN / email / phone) are redacted **before** they
reach the model or the traces — with **zero changes to business code**. Proven
end-to-end via the LangSmith API.

---

## What we set up

A guardrail that scans every LLM request and replaces PII with placeholders:

```
Customer message (real SSN 987-65-4321)
        │
        ▼
[ before_model_callback ]  regex → [REDACTED_SSN] / [REDACTED_EMAIL]   ← governance layer
        │  (runs BEFORE the model call AND before the trace is recorded)
        ▼
LLM + Cloud Trace + LangSmith  only ever see  [REDACTED_SSN]
        │
        ▼
Refund still processes correctly (order_id drives the decision, not the SSN)
```

It is an ADK **Plugin** (`guardrails.py`, `PIIRedactionPlugin`), registered at
the serve layer — the same decoupling as tracing. `agent.py`, `tools.py`, and
every SKILL.md are untouched (verified by grep).

Why it also protects the traces: ADK runs `before_model_callback` **before**
`trace_call_llm` (`base_llm_flow.py` ~line 1345 vs ~1416), so the redaction is
already applied when the span is recorded. One governance pillar (guardrail)
protects another (observability).

---

## Proven — before / after (via LangSmith API)

| | Without guardrail | With guardrail |
|---|---|---|
| Test SSN | `123-45-6789` | `987-65-4321` |
| Plaintext SSN in LangSmith | ❌ leaked in 6 runs | ✅ **0 runs** |
| `[REDACTED_SSN]` present | — | ✅ 3 runs |
| Refund decision | correct | **still correct** (ESCALATE / PAST_REFUND_WINDOW) |
| Business code changed | — | **none** |

The decision is unaffected because the SSN is never part of the refund logic —
the pipeline identifies the customer by `order_id → customer_id`.

---

## How to run

```bash
cd adk_refund && source venv/bin/activate
set -a; source .env.local; set +a                # LangSmith key
export GOOGLE_CLOUD_PROJECT=linkhealth-care-2024
export PII_GUARDRAIL=on                           # or "off" to see the leak
python serve_dual_trace.py
```

Send a refund whose message contains an SSN, then query LangSmith
(`/api/v1/runs/query`) and grep the run inputs for the SSN vs `[REDACTED_SSN]`.

---

## ADK plugin gotchas (cost two debugging rounds)

1. `get_fast_api_app(extra_plugins=...)` wants **fully-qualified name strings**
   (`"guardrails.PIIRedactionPlugin"`), **not instances** — instances are
   silently ignored and the callback never fires.
2. ADK instantiates the class passing a `name` kwarg, so the plugin `__init__`
   **must accept `name`**: `def __init__(self, name="pii_redaction"): super().__init__(name=name)`.
   Otherwise you get a WARNING (easy to miss) and no redaction.

---

## Concepts — the design space for sensitive data

Redaction is only the simplest technique. Choose by what downstream needs:

| Technique | Looks like | Same person? | Recover real value? | Use when |
|-----------|-----------|--------------|---------------------|----------|
| **Redaction** (ours) | `[REDACTED_SSN]` | ❌ | ❌ | value never needed downstream |
| Masking | `***-**-4321` | partial | ❌ | human verification |
| Hashing | `hash=a1b2c3…` | ✅ | ❌ | group by person, never reveal |
| **Tokenization** | `TKN_7f3a` | ✅ | ✅ (via secure vault) | must reveal later |
| Encryption | `enc(…)` | depends | ✅ (with key) | reversible, rarely in logs |

**Reveal-at-the-boundary pattern:** to give the real value back to the customer
at the end, use tokenization (not redaction — redaction is lossy). The vault
holds `token ↔ real`; the pipeline carries only the token; de-tokenization
happens at a trusted **egress boundary that is NOT traced**. If a tool truly
needs the real value, it de-tokenizes internally and emits only the token. Best
practice: the LLM never touches real PII — a non-LLM egress component
substitutes it into the final message.

**Build vs buy / managed vs custom:**

| | Custom code (ours) | Managed (platform) |
|---|---|---|
| Example | `guardrails.py` regex Plugin | Model Armor, Sensitive Data Protection (DLP) |
| Deploy | real code, ships **with the agent** | configure a policy — **no code deploy** |
| Registration | local: `serve_dual_trace.py`; cloud: deploy config | platform-side |

Our hand-rolled guardrail is the "understand it locally" version of what
**Model Armor** does as a managed service on Gemini Enterprise (roadmap #6).
Deep sensitive-data code (tokenization, KMS) is not hand-written — you wire to
managed services; your governance code stays thin.

---

## The one concept to remember

> Governance is another cross-cutting layer, decoupled from business logic —
> exactly like observability. `agent.py` / SKILL.md never change. Complexity
> moves **into** the governance layer (and, for deep needs, into managed
> platform services), and **out of** the business code.
