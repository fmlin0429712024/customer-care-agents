# 01 — Coordinator design & the handoff contract

**Status: 🟡 M1 — design only (no code).** This page fixes the coordinator's
*contract* before any implementation. The contract is the part that survives
unchanged from a local prototype (M2, in-process) all the way to a remote
**A2A** call (M5) — so it is worth getting right first.

---

## Coordinator vs worker — the one distinction

| | Worker (refund) | Coordinator (front desk) |
|---|---|---|
| Who decides the next step | **the programmer** (wired) | **the LLM** (reads intent at runtime) |
| Orchestration | `SequentialAgent` — fixed order | LLM-routed — dynamic |
| Why | task steps are inherently fixed | the customer's next sentence is unknowable |

A worker can hard-wire `lookup → decide → screen → respond` because those steps
never change. A coordinator cannot: whether the customer wants a refund, asks
about shipping, or just chats is decided by *what they say this turn*. So control
flow moves into the LLM. In one line: **the coordinator is an intent classifier
+ slot filler + dispatcher + relayer**, and the worker is a black box it cannot
see inside.

---

## Part 1 — Intent schema (4 classes, only 1 is real)

Kept minimal on purpose. Every customer message maps to one of:

| intent | routes to | status |
|---|---|---|
| `refund` | refund worker (real) | ✅ real call |
| `billing` | billing specialist | 🔲 stub: "specialist not online yet" |
| `shipping` | shipping specialist | 🔲 stub: "specialist not online yet" |
| `other` | stay in conversation, clarify / chat | — |

The stubs exist to prove the architecture is **extensible**: adding a specialist
is one row in the routing table, with no change to the coordinator's core.

---

## Part 2 — The handoff contract  ⭐ (the line that becomes A2A)

The coordinator and worker exchange **structured data only** — never the raw
chat. This schema is the seed of the future A2A message and the security
boundary.

```
dispatch (coordinator → worker)        result (worker → coordinator)
┌────────────────────────┐            ┌──────────────────────────────┐
│ intent:   "refund"     │            │ decision:   APPROVE|ESCALATE  │
│ order_id: "67890"      │   ────▶    │             |REJECT           │
│                        │   ◀────    │ reason_code:"AUTO_APPROVED"   │
│ (that's it)            │            │ ticket_id:  "T-123" | null    │
└────────────────────────┘            └──────────────────────────────┘
```

The worker is a **black box**: the coordinator does not know refund policy. It
knows only "give it an `order_id`, get back a `decision`."

---

## Part 3 — The per-turn loop

```
customer says something
   │
   ▼
① classify intent ───────────────────────┐
   ├─ other  → clarify / chat, stay in convo
   ├─ billing/shipping → return stub message
   └─ refund → ②
              │
              ▼
   ② required slots filled? (refund needs order_id)
        ├─ missing → ask for the order number (no dispatch)   ← slot filling
        └─ filled  → ③ dispatch to worker
                    │
                    ▼
   ③ receive decision → ④ relay to the customer in a warm voice
```

**Slot filling** (step ②) — gathering the worker's required inputs *before*
dispatch — is a core, transferable agentic pattern. In A2A terms, an unfilled
slot is a task in the `input-required` state.

---

## Part 4 — Boundaries (what the coordinator never does)

- ❌ never decides refund eligibility (that is the worker's policy)
- ❌ never invents order data or ticket numbers
- ✅ only: understand → fill slots → dispatch → relay

---

## How this contract becomes A2A (M5 preview)

A2A is an open protocol for agents to **discover and delegate to each other** as
peers over the network. Contrast with MCP:

- **MCP** connects an agent to **tools/resources** (vertical: "I need a capability").
- **A2A** connects an agent to **another agent** (horizontal: "I'll delegate a whole task").

Mapping this design onto A2A's core pieces:

| A2A concept | In this project |
|---|---|
| **Agent Card** (`/.well-known/agent.json`) | the worker advertises: "I'm `refund`; send `order_id`, get `decision`" |
| **Task** (lifecycle: submitted → working → input-required → completed) | one dispatch = one task |
| **Message / Artifact** | `{order_id}` is the message; `{decision, ...}` is the artifact |
| **Auth** (OAuth / API key) | the identity & security boundary between the two agents |

The payoff: **M2 (in-process `sub_agent`) and M5 (remote A2A) share this exact
contract.** Going remote swaps an in-process call for HTTP + an Agent Card + auth
— the design does not change. That is why the contract is fixed first.

---

## Open design questions (to resolve before M2)

1. Should the dispatch payload include the customer's raw utterance, or only the
   extracted `order_id`? (Minimal = cleaner boundary; raw = more worker context.)
2. Keep 4 intents, or start with just `refund` + `other`?
3. Where does slot filling live — coordinator only, or can the worker request
   missing input back (the `input-required` path)?
