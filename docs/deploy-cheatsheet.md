# Deploy Cheat Sheet — localhost → Cloud Run (both agents)

Both agents carry the **full application-level harness** (Way 1). The same serve
files run locally and on Cloud Run — `0.0.0.0:$PORT`, backends swap via env.

> **✅ Deployed & verified (us-central1):** two separate containers = real A2A.
> - `refund-a2a`  → https://refund-a2a-51058313466.us-central1.run.app
> - `care-agent`  → https://care-agent-51058313466.us-central1.run.app
>
> Verified live: care redacts a PII email (guardrail), delegates over A2A/HTTPS,
> refund runs its 4 stages on its own container and returns the decision
> (order 67890 → APPROVE; 12345 → ESCALATE).

## What each agent now has

| | refund (worker) | care (coordinator) |
|---|---|---|
| Agent core | `refund_agent/` | `care_agent/` (+ tools: `set_order_id`, `get_order_id`, `load_memory`) |
| Guardrail (PII) | `guardrails.py` | `guardrails.py` (**first line**) |
| Trace | `serve_dual_trace.py` (dual export) | `serve.py` (`TRACE_TO_CLOUD=on`) |
| A2A serve (Cloud-Run-ready) | `a2a_server.py` — `0.0.0.0:$PORT`, `A2A_PUBLIC_URL` for the card | consumes it via `REFUND_A2A_BASE_URL` |
| Container | `Dockerfile` | `Dockerfile` + `requirements.txt` |

---

## 1 · Run locally (all harness, 2 terminals)

```bash
# terminal 1 — refund A2A server (has the Agent Card care calls)
cd refund-agent/adk_refund
.venv/bin/python a2a_server.py                     # binds 0.0.0.0:8043

# terminal 2 — care coordinator, full harness (guardrail + trace-ready + session/memory/state + A2A)
cd customer-care-agent/adk_care
.venv/bin/python serve.py                          # binds 0.0.0.0:8042
# open http://localhost:8042  → pick care_agent
```

Verify (what we tested): a refund request with a PII email → care logs
`[GUARDRAIL] … redacted 1 part(s)`, delegates over A2A, refund runs its 4 stages
and returns a real ticket. Standalone harness demos:

```bash
cd customer-care-agent/adk_care
.venv/bin/python m3_memory_demo.py        # memory across sessions
.venv/bin/python session_state_demo.py    # state across turns
```

---

## 2 · Deploy to Cloud Run (Way 1)

Project `linkhealth-care-2024` · region `us-central1` · SA
`refund-agent-dev@linkhealth-care-2024.iam.gserviceaccount.com`.

**Order matters:** deploy the worker first (care needs its URL).

### 2a · refund worker — as the A2A endpoint

The A2A container entrypoint is `a2a_server.py` (not the playground
`serve_dual_trace.py`). Set the Dockerfile `CMD` to `["python","a2a_server.py"]`
for this service, then:

```bash
cd refund-agent/adk_refund   # Dockerfile CMD = a2a_server.py; installs a2a extras
gcloud run deploy refund-a2a \
  --source=. --region=us-central1 \
  --service-account=refund-agent-dev@linkhealth-care-2024.iam.gserviceaccount.com \
  --allow-unauthenticated

# Two env fixes after first deploy (both learned the hard way):
RURL=$(gcloud run services describe refund-a2a --region=us-central1 --format='value(status.url)')
gcloud run services update refund-a2a --region=us-central1 --update-env-vars=\
A2A_PUBLIC_URL=$RURL,\
GOOGLE_GENAI_USE_VERTEXAI=TRUE,GOOGLE_CLOUD_PROJECT=linkhealth-care-2024,GOOGLE_CLOUD_LOCATION=us-central1
```

> **Two gotchas here:**
> 1. **Agent Card URL** — `to_a2a` bakes the card `url` from host/port; on Cloud
>    Run it must be the public `*.run.app`, hence `A2A_PUBLIC_URL`. Verify:
>    `curl -s $RURL/.well-known/agent-card.json | jq .url`.
> 2. **Model auth** — the worker's `.env` is dockerignored, so the container has
>    no auth config and defaults to API-key mode → *"No API key provided."* Set
>    `GOOGLE_GENAI_USE_VERTEXAI=TRUE` (+ project/location) so it uses the service
>    account. The SA needs `roles/aiplatform.user`.

> **The one A2A-on-Cloud-Run gotcha:** `to_a2a` bakes the Card's `url` from
> host/port. Locally that's `localhost:8043`; on Cloud Run it must be the public
> `*.run.app` URL — hence `A2A_PUBLIC_URL`. Verify:
> `curl -s $RURL/.well-known/agent-card.json | jq .url` → should be `$RURL`.

### 2b · care coordinator — pointing at the worker's URL

```bash
cd customer-care-agent/adk_care
gcloud run deploy care-agent \
  --source=. --region=us-central1 \
  --service-account=refund-agent-dev@linkhealth-care-2024.iam.gserviceaccount.com \
  --allow-unauthenticated \
  --set-env-vars=REFUND_A2A_BASE_URL=$RURL,TRACE_TO_CLOUD=on,PII_GUARDRAIL=on
```

Open the care URL → same conversation as local, now fully on Cloud Run.

### 2c · persistence (Cloud Run is stateless / multi-instance)

InMemory session/memory don't survive across instances. When you need durable
state, set on `care-agent` (no code change — "swap the backend, not the concept"):

```bash
--set-env-vars=SESSION_SERVICE_URI=<db-uri>,MEMORY_SERVICE_URI=<store-uri>
```

---

## Gotchas seen

| # | Symptom | Fix |
|---|---------|-----|
| 1 | `ModuleNotFoundError: a2a` in the container | add `google-adk[a2a]` + `a2a-sdk[http-server]` to the Dockerfile pip install |
| 2 | Agent Card advertises `localhost` from Cloud Run | set `A2A_PUBLIC_URL` on the refund service, redeploy env |
| 3 | refund model: *"No API key provided"* | its `.env` is dockerignored → set `GOOGLE_GENAI_USE_VERTEXAI=TRUE` (+ project/location) so it uses the SA |
| 4 | Cloud Trace writes 403 | grant SA `roles/cloudtrace.agent` |
| 5 | memory/state lost after a request on Cloud Run | externalize via `SESSION_SERVICE_URI` / `MEMORY_SERVICE_URI` |

## Still open (honest)

- **Distributed tracing across A2A** — each service traces itself, but stitching
  `care → A2A → refund` into a single end-to-end trace needs trace-context
  propagation across the hop. Observability polish, not a blocker.
- **Persistence** is still InMemory on Cloud Run — fine for a demo, but memory/
  state won't survive across instances until `*_SERVICE_URI` point at a store.
