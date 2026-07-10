# 05 — Deployment: Agent Engine (managed agent tier)

**Status: ✅ Done.** Deployed the same agent to **Vertex AI Agent Engine**
(a.k.a. Reasoning Engine) — the fully managed agent runtime. This is the tier
*above* Cloud Run: Cloud Run gave us managed **infrastructure** (container +
scaling); Agent Engine gives us managed **agent services** on top — a hosted
runtime, managed **Sessions**, a built-in playground, and the entry point that
**Agentspace** registers against.

Resource:
`projects/linkhealth-care-2024/locations/us-central1/reasoningEngines/4456697210108641280`
· [Console playground](https://console.cloud.google.com/vertex-ai/agents/agent-engines/locations/us-central1/agent-engines/4456697210108641280/playground?project=linkhealth-care-2024)

**Verified on Agent Engine (end-to-end, via `stream_query`):**

| Order | Decision | Evidence |
|-------|----------|----------|
| 67890 | APPROVE — AUTO_APPROVED | $49, delivered 2 days |
| 12345 | ESCALATE — PAST_REFUND_WINDOW | real ticket `ESCA-20260710155404-14BF14`, **read back from Firestore locally** (managed data layer persists cross-runtime) |
| 99999 | REJECT — ORDER_NOT_FOUND | not found |

Same SKILL.md policy, same `tools.py`, same pipeline — only **auth mode** and
one **Firestore project pin** differed from local. No business logic changed.

---

## Deploy command (CLI, assistant-driven)

```bash
adk deploy agent_engine \
  --project=linkhealth-care-2024 \
  --region=us-central1 \
  --agent_engine_id=4456697210108641280 \   # omit on first deploy to create new
  --display_name="Refund Agent" \
  --trace_to_cloud \
  refund_agent
```

`adk` packages `refund_agent/` (including `requirements.txt` and `.env`),
builds a container, and hands it to the managed runtime. `--agent_engine_id`
updates in place; drop it to mint a new engine.

---

## The two gotchas that actually mattered

Deployment succeeded on the first `exit 0`, but the agent was broken at
runtime. **Lesson: never call an Agent Engine deploy "green" from `exit 0` —
drive a real query, and if you get 0 events, read the runtime logs.**

```bash
gcloud logging read \
  'resource.type="aiplatform.googleapis.com/ReasoningEngine"
   AND resource.labels.reasoning_engine_id="4456697210108641280"
   AND severity>=ERROR' \
  --project=linkhealth-care-2024 --freshness=10m --format='value(textPayload)'
```

### 1. Auth: managed Sessions reject API keys (401)

Local `adk web` used AI Studio **API-key** mode (`GOOGLE_GENAI_USE_VERTEXAI=FALSE`
+ `GOOGLE_API_KEY`) for convenience, and that `.env` shipped with the deploy.
On Agent Engine, `create_session` failed with:

```
401 UNAUTHENTICATED — API keys are not supported by this API.
method: SessionService.CreateSession
```

Agent Engine's **managed Session service** (`aiplatform.googleapis.com`) only
accepts **OAuth2** — the runtime's service account — never API keys. The
symptom was nasty: `stream_query` yielded **0 events silently**; only explicit
`create_session` surfaced the 401.

**Fix — run the agent in Vertex mode everywhere:**

```dotenv
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=linkhealth-care-2024
GOOGLE_CLOUD_LOCATION=us-central1
# API key kept only as a commented local fallback
```

Then auth is **ADC in both places**: locally your
`gcloud auth application-default login`; on Agent Engine the reasoning-engine
service account. One auth story. Grant that SA
(`service-<PROJECT_NUMBER>@gcp-sa-aiplatform-re.iam.gserviceaccount.com`):

- `roles/aiplatform.user` — Vertex Gemini calls **and** the Session service
- `roles/datastore.user` — Firestore reads/writes

### 2. Firestore wants the project *ID*, not the number

After auth was fixed the pipeline started, `order_lookup` fired its tool call —
then died with:

```
404 The database (default) does not exist for project 51058313466
400 Invalid project id in name!
```

`51058313466` is the project **number**. On Agent Engine,
`GOOGLE_CLOUD_PROJECT` resolves to the *number* (platform-set / metadata
auto-detect), and `dotenv` does **not** override an already-set env var, so our
`.env` ID was ignored. Vertex/Gemini happily accept a project number (that's why
sessions worked), but **Firestore only accepts the project ID**.

**Fix — pin the ID in a var the platform won't touch** (`tools.py` prefers it):

```dotenv
REFUND_FIRESTORE_PROJECT=linkhealth-care-2024
```

```python
_FIRESTORE_PROJECT = (
    os.environ.get("REFUND_FIRESTORE_PROJECT")
    or os.environ.get("GOOGLE_CLOUD_PROJECT")
)
_db = firestore.Client(project=_FIRESTORE_PROJECT)
```

---

## Cloud Run vs Agent Engine — what moved up a tier

| | Cloud Run (milestone 03) | Agent Engine (this one) |
|---|---|---|
| Manages | container + autoscaling infra | agent **runtime + services** |
| Sessions | you wire (in-memory / your store) | **managed** Session service |
| Auth to Google APIs | your service account | **reasoning-engine** SA (OAuth only) |
| Entry point | HTTP URL you own | `stream_query` / console playground / **Agentspace** |
| Frontend | you serve the playground | playground provided |

Cloud Run = managed **infrastructure**. Agent Engine = managed **agent
platform** — and the thing Gemini Enterprise / **Agentspace** plugs into next
(milestone 07).

---

## Next: Agentspace (milestone 07)

The engine is live and testable without the local playground. Register it to
**Agentspace** (portal) to get the enterprise surface — discovery, governance,
end-user access — on top of this same deployed engine. `stream_query` and the
console playground already work as the interim test path.
