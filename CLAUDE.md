# Customer Service Agents — Workspace

> **▶ Handoff — resume here (for a fresh session):**
> This folder was renamed from `customer-refund-agent` → `customer-care-agents`;
> the Claude Code memory was migrated along with it, so recall should still work
> (if not, read `MEMORY.md`). **Where we are:** the `refund-agent` worker is
> **done and deployed to Agent Engine**; the workspace was just restructured into
> a worker + coordinator system. **Next action:** start **M1 — LLM-routed
> orchestration (concept only)** for the `customer-care-agent` coordinator.
> **How to teach me (the user):** concept-first, big-picture-first, one step at a
> time, repetition welcome; explain the concept, let me say it back in my own
> words, *then* go hands-on. See [[user-learning-style]].

An **agent system**, not a single agent. Two agents developed side by side:

```
customer-refund-agent/            ← workspace root (path unchanged — memory preserved)
├── refund-agent/                 ← WORKER  · the specialist (DONE ✅)
│   └── adk_refund/               ·   1 orchestrator (SequentialAgent) + 4 sub-agents
│                                 ·   deployed to Agent Engine, Firestore, tracing, eval
├── customer-care-agent/          ← COORDINATOR · the conversational front desk (TO BUILD)
│                                 ·   long session · Memory Bank · context mgmt · routing
└── .claude/skills/
    ├── customer-refund/          ·   (lives under refund-agent/, self-contained)
    └── customer-care/            ·   coordinator skill (skeleton — M1)
```

## The vision (why two folders)

The refund agent is a **worker** — it does one job (30s), then responds. Upstream
sits a **coordinator**: a conversational agent that talks to the customer, and
when the topic turns to a refund, **routes** the request to the refund worker.

From a coarse view, the whole refund worker is **one black box** with one input
and one output — agents compose (encapsulation / fractal). The coordinator can
call the worker in-process (`sub_agents` / `AgentTool`) or, once both are
independently deployed, over the **A2A protocol**.

This is deliberately the same architecture as **Gemini Enterprise / Agentspace**:
a conversational front door that dispatches to registered specialist agents.

## Status & roadmap

| Agent | Role | Status |
|-------|------|--------|
| `refund-agent` | specialist worker | ✅ done — deployed to Agent Engine |
| `customer-care-agent` | conversational coordinator | ⬜ to build (M1–M6) |

Learning path for the coordinator (see the blueprint artifact):

1. **M1** — LLM-routed orchestration (concept)
2. **M2** — minimal coordinator → in-process `sub_agents` call to refund worker
3. **M3** — Memory Bank (remember the customer across turns)
4. **M4** — context management (long conversations)
5. **M5** — split deployments + **A2A** remote call
6. **M6** — register to Gemini Enterprise (full circle)

## Conventions (inherited from refund-agent)

- **Policy lives in `SKILL.md`**, hard-copied verbatim into the ADK agent. Never
  re-author business logic in Python. Host wiring (tools, state, memory) differs
  per environment; the skill text does not.
- **Data access lives in `tools.py`** as ADK FunctionTools — deterministic I/O
  only, no policy.
- **Secrets never committed.** `.env` files are gitignored (root `.gitignore`
  applies recursively). Auth on Agent Engine = Vertex/OAuth service account, not
  API keys.

## Notes for future sessions

- This root path is intentionally **unchanged** (`customer-refund-agent`) so the
  Claude Code memory namespace is preserved. The folder may be **renamed later**
  (e.g. `customer-care-agents`) once the coordinator work begins in earnest.
- The old GitHub remote was pushed (final snapshot) then disconnected; the repo
  is currently **local only**. A fresh GitHub repo will be created later.
