# 03 — A2A, local, step by step

**Status: ✅ working.** The coordinator (`care_agent`) calls the refund worker
(`refund_agent`) over the **A2A protocol**, both running on localhost. This page
is the exact runbook + the gotchas we hit. Official docs:
[expose](https://adk.dev/a2a/quickstart-exposing/) ·
[consume](https://adk.dev/a2a/quickstart-consuming/).

```
care_agent  :8042 (dev-ui)  ──A2A HTTP──▶  refund_agent  :8043 (A2A server)
        client                                    server (Agent Card)
```

---

## 0 · One-time setup (per agent, self-contained)

Each ADK project gets **its own venv**. (The pre-rename venvs are dead — their
scripts hardcode the old absolute path; recreate, don't repair. See
[[adk-local-run-and-venv-gotcha]].)

```bash
# refund worker
cd refund-agent/adk_refund
python3 -m venv .venv && .venv/bin/pip install -e .
.venv/bin/pip install "google-adk[a2a]" "a2a-sdk[http-server]"

# care coordinator
cd customer-care-agent/adk_care
python3 -m venv .venv && .venv/bin/pip install -e .
.venv/bin/pip install "google-adk[a2a]" "a2a-sdk[http-server]"
```

> **Gotcha:** `to_a2a` needs the A2A SDK, which is **not** pulled in by default.
> Missing it → `ModuleNotFoundError: No module named 'a2a'`, then
> `sse-starlette ... required`. Both fixed by the two extras above.

---

## 1 · Expose the worker as an A2A **server** (`to_a2a`)

The worker's `agent.py` stays **byte-identical**. Add one wrapper file:

```python
# refund-agent/adk_refund/a2a_server.py
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / "refund_agent" / ".env")   # Vertex + Firestore

from google.adk.a2a.utils.agent_to_a2a import to_a2a
from refund_agent.agent import root_agent

a2a_app = to_a2a(root_agent, port=8043)   # auto: Agent Card + routes + task store
```

Run it (this is the "deploy", locally):

```bash
cd refund-agent/adk_refund
.venv/bin/uvicorn a2a_server:a2a_app --host localhost --port 8043
```

Verify the **Agent Card** (the frozen interface, auto-generated):

```bash
curl -s http://localhost:8043/.well-known/agent-card.json | python3 -m json.tool
# name: refund_pipeline · protocolVersion: 0.3.0 · url: http://localhost:8043
```

> The A2A server is **headless** — no chat playground. It's a machine endpoint
> other agents call. (Load `.env` *before* importing the agent: `tools.py`
> builds a Firestore client at import time.)

---

## 2 · Consume it from the coordinator (`RemoteA2aAgent`)

In the coordinator's `agent.py`, the refund handoff is **host wiring** (never in
the SKILL.md):

```python
from google.adk.agents.remote_a2a_agent import (
    AGENT_CARD_WELL_KNOWN_PATH, RemoteA2aAgent,
)

refund_remote = RemoteA2aAgent(
    name="refund_agent",
    description="Remote refund specialist reached over A2A ...",
    agent_card=f"http://localhost:8043{AGENT_CARD_WELL_KNOWN_PATH}",
    use_legacy=False,
)

root_agent = Agent(
    model="gemini-2.5-flash",
    name="care_agent",
    instruction=_coordinator_skill + _A2A_HOST_WIRING,   # "delegate refunds to refund_agent"
    sub_agents=[refund_remote],
)
```

Run the coordinator's playground:

```bash
cd customer-care-agent/adk_care
.venv/bin/adk web --port 8042 .
```

---

## 3 · See it work (one window: the care dev-ui)

`http://127.0.0.1:8042` → pick `care_agent`, then:

```
you:   I want my money back
care:  I can help with that. What is your order number?      ← slot-filling
you:   order 12345
```

In the **Events / Traces** tab you see the A2A handoff, live:

```
#4  ⚡ transfer_to_agent("refund_agent")
#5  ✓  transfer_to_agent   care_agent → refund_agent          ← the A2A call
#6  refund_agent:  ORDER LOOKUP → REFUND DECISION (ESCALATE / PAST_REFUND_WINDOW)
                   → FRAUD SCREEN → customer reply + ticket ESCA-...
```

**What the window shows / hides** — care's reasoning, the outgoing call, and the
result are visible; the worker's *internal* 4 stages run in its own process
behind the Agent Card. That hiding **is** the separation of concerns.

Known-good test orders: `67890`→APPROVE · `12345`→ESCALATE(past window) ·
`11111`→ESCALATE(in transit) · `99999`→REJECT(not found).

---

## Why this shape (the mainstream call)

- **A2A**, not in-process `sub_agent`, because the real scenario is *one
  coordinator + many independent worker agents* — separate deploys, separate
  teams, frozen interfaces. That's exactly A2A's job (and the Gemini Enterprise /
  Agentspace pattern this project mirrors).
- **Call-and-wait** (synchronous request/response): the coordinator needs the
  decision before it can reply. Not fire-and-forget, not streaming.
- **MCP would be the choice if the worker were a *tool*, not an *agent*.**
  Rule of thumb: **MCP = agent→tools, A2A = agent→agent.**
