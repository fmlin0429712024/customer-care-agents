# 03 — Deployment: Cloud Run (single region)

**Status: ✅ Done.** Deployed the agent — with its tracing and PII guardrail — to
**Cloud Run in `us-central1`**. Live URL:
`https://refund-agent-xwbl4hgnja-uc.a.run.app`. Multi-region + load balancer is
**out of scope** (conceptual note at the end).

**Verified on Cloud Run:** playground served at the public URL · refund runs
end-to-end (order 12345 → ESCALATE, real ticket) · both OTel exporters
initialized (Cloud Trace + LangSmith) · guardrail fired 6× and redacted the SSN
(0 plaintext in LangSmith, `[REDACTED_SSN]` present). Same experience as local,
only host wiring + runtime config differed.

Goal: prove the same agent, tracing, and guardrail run unchanged in the cloud —
only the *host wiring and runtime config* differ.

---

## Scope (locked — no creep)

**In scope**
- **One** container, Cloud Run, **`us-central1` only**.
- Path B (custom `serve_dual_trace.py` entrypoint) → keeps Cloud Trace +
  LangSmith + guardrail.
- Wire the 4 runtime things: LangSmith key (via `--set-env-vars` for now),
  `cloudtrace.agent` IAM grant, `GOOGLE_CLOUD_PROJECT`, `REFUND_DB_PATH=/tmp`.
- Reuse service account `refund-agent-dev`.
- **One environment** (no dev/prod split), on project `linkhealth-care-2024`.

**Out of scope (deferred, on purpose)**
- Multi-region + load balancer → concept only.
- dev/prod separation → one environment now.
- SQLite → Firestore → milestone 2.5 (keep `/tmp` SQLite; tickets ephemeral, OK).
- Agent Engine / Gemini Enterprise → later tier.
- Custom production frontend → use the playground UI.
- Secret Manager hardening → note it; use `--set-env-vars` for learning.

**Done when**
1. `https://…run.app` serves the playground; a refund runs end-to-end.
2. Cloud Trace shows the trace (TAO waterfall).
3. LangSmith shows the runs.
4. Guardrail redacts an SSN (quick before-model check).

---

## Mental model: code in the container vs config injected at runtime

Cloud Run = **serverless containers**. Google runs your container, auto-scales
it (including to zero), and hides the cluster. The container is a sealed,
shippable artifact, so:

| Goes **inside** the container (build time) | Injected **from outside** (runtime) |
|---|---|
| `refund_agent/`, `serve_dual_trace.py`, `guardrails.py` | LangSmith API key (secret) |
| Python deps (ADK, OTel exporters) | GCP identity / permissions |
| bundled `skills/` + `orders.json` | `GOOGLE_CLOUD_PROJECT`, `REFUND_DB_PATH` |

Rule: **never bake secrets/environment values into the image.** Code is built
once; config/secrets are supplied per environment.

---

## The 4 runtime things to set up (not code)

| # | Thing | How | If missing |
|---|-------|-----|-----------|
| 1 | LangSmith API key | env var / Secret Manager | LangSmith gets nothing (code skips it) |
| 2 | Cloud Trace permission | grant the run service account `roles/cloudtrace.agent` | trace writes 403 |
| 3 | `GOOGLE_CLOUD_PROJECT` | env var | exporter has no target |
| 4 | DB path | env var `REFUND_DB_PATH=/tmp/refund.db` | write fails (fs read-only) |

Service account: reuse the existing **`refund-agent-dev@linkhealth-care-2024.iam.gserviceaccount.com`**.

---

## Two deployment paths

### Path A — ADK native (simplest, Cloud Trace only)

```bash
adk deploy cloud_run \
  --project=linkhealth-care-2024 --region=us-central1 \
  --service_name=refund-agent --trace_to_cloud
```

Gives Cloud Trace. Does **not** bring LangSmith dual-export or the guardrail,
because those live in our custom launcher, not ADK's default serving.

### Path B — custom entrypoint (recommended: keeps dual-export + guardrail)

Use `serve_dual_trace.py` as the container entrypoint so everything we
demonstrated carries over. Required tweak: bind `0.0.0.0` and read `$PORT`
(Cloud Run sets it):

```python
PORT = int(os.environ.get("PORT", 8001))
uvicorn.run(app, host="0.0.0.0", port=PORT)
```

`Dockerfile`:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . /app
RUN pip install -e . \
    opentelemetry-exporter-gcp-trace opentelemetry-exporter-otlp-proto-http
ENV PII_GUARDRAIL=on REFUND_DB_PATH=/tmp/refund.db
CMD ["python", "serve_dual_trace.py"]
```

Deploy + wire the 4 runtime things:

```bash
# 2) grant the service account trace-write
gcloud projects add-iam-policy-binding linkhealth-care-2024 \
  --member=serviceAccount:refund-agent-dev@linkhealth-care-2024.iam.gserviceaccount.com \
  --role=roles/cloudtrace.agent

# deploy (1,3,4 as env vars; from source builds the image for you)
gcloud run deploy refund-agent \
  --source=. --region=us-central1 \
  --service-account=refund-agent-dev@linkhealth-care-2024.iam.gserviceaccount.com \
  --set-env-vars=GOOGLE_CLOUD_PROJECT=linkhealth-care-2024,REFUND_DB_PATH=/tmp/refund.db,PII_GUARDRAIL=on \
  --set-env-vars=LANGSMITH_API_KEY=<from Secret Manager in real use>,LANGSMITH_PROJECT=refund-agent \
  --allow-unauthenticated
```

Result: a public `https://refund-agent-....a.run.app` URL serving the same
playground, with tracing and the guardrail working.

---

## Known caveat: SQLite is ephemeral here

The container filesystem is temporary and per-instance:

- `orders` table — re-seeded from bundled `orders.json` each cold start → fine.
- `tickets` table — written at runtime → **lost on restart, not shared across
  instances.** Acceptable for this demo; **not** for production.

Fix is a **separate milestone (03.5)**: swap SQLite for **Firestore / Cloud
SQL**. Because data access is isolated in `tools.py`, that swap touches only
`tools.py` — `agent.py` and the SKILL.md never change.

---

## Out of scope: multi-region + load balancer (concept only)

Cloud Run is **regional** — one deploy = one region = one `*.run.app` URL. Going
global is deliberate cloud-infra work, not agent work:

```
User → [ Global External Application Load Balancer : one URL/IP ]
           ├─ (nearest) → Cloud Run  us-central1
           └─ (nearest) → Cloud Run  europe-west1
```

Terminology: the extra tier is a **Load Balancer** (Serverless NEG per region);
**redundancy / failover** is the *benefit*, not the tier's name. We only
**discuss** this — we deploy a single region (`us-central1`).

---

## The one concept to remember

> The agent, its tracing, and its guardrail deploy **unchanged**. What changes
> going to the cloud is never the business logic — only the **host wiring**
> (entrypoint) and **runtime config** (identity, secrets, paths). Code is built
> into the container; everything environment-specific is injected from outside.
