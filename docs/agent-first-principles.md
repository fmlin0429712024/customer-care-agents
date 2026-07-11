# Agent Engineering — First Principles & the 2026 Landscape

A deployment-agnostic mental model for autonomous agents, and how today's two
dominant architectures (self-hosted **digital employee** vs multi-tenant
**enterprise platform**) are the *same engine* tuned for opposite goals.

The thesis in one line:

> **There is one loop. Everything else — frameworks, platforms, governance — is
> packaging around it. Capabilities have converged; what differs is philosophy.**

---

## 1 · The one loop (the first principle)

Every agent, stripped to the atom, is a **feedback loop**:

```
 perceive ──▶ decide (LLM) ──▶ act (tools) ──▶ update state ──┐
    ▲                                                          │
    └──────────────────────────────────────────────────────────┘
      each step: assemble context from (history + state + memory),
      bounded by a fixed context window
```

Read it as a **four-stroke engine** — the four moves are irreducible:

| Stroke | In an agent | Why it can't be removed |
|--------|-------------|-------------------------|
| **intake** — perceive | take in new input (user msg / tool result) | remove it → blind |
| **compression + ignition** — decide | the LLM reasons and picks the next action | remove it → a dumb script, not an agent |
| **power** — act | execute a tool, affect the world | remove it → a chatbot, can't do anything |
| **exhaust + recharge** — update state | write the result back; it becomes the next intake | remove it → can't build on its own actions |

**The definition that follows:**

> A single LLM call is **not** an agent. **Agent = LLM + tools + a loop that
> feeds results back.** The loop *is* the definition of the field.

**Fuel and cylinder:** the "fuel/air mix" burned each ignition is the **context**
assembled that step; the **fixed context window** is the cylinder displacement.
Tuning the mix = context engineering (§3).

### 1.1 · ReAct / TAO, and why the "variations" aren't new engines

The canonical name for this loop is **ReAct** (Reason + Act), whose cycle steps
are **TAO** — *Thought → Action → Observation*. ReAct ≈ TAO ≈ the loop above;
ReAct's one signature is that the reasoning ("Thought") is written out explicitly
before each action.

The other named patterns are **not** new engines — each is *the same loop + one
topping*:

| Pattern | = loop + | The added topping |
|---------|----------|-------------------|
| **ReAct** | (the atom) | explicit reasoning trace |
| **Reflexion** | + self-critique | look back at what failed, retry |
| **Plan-and-Execute** | + up-front plan | plan first, then step through |
| **Tree-of-Thoughts** | + branching search | try several paths, pick the best |

**Practical rule:** memorize **one** loop. For any new pattern, don't memorize it
— ask *"what did it add on top of the loop?"* and reduce it back to `loop + X`.

---

## 2 · The four primitives (session · state · context · memory)

| Term | Precisely | Crosses conversations? |
|------|-----------|------------------------|
| **Session** | one conversation thread / the container (holds this conversation's events) | ❌ |
| **State** | a key-value scratchpad on a session — structured facts, e.g. `{intent, order_id, decision}` | ❌ |
| **Context** | the slice actually assembled into the LLM's prompt window **this turn** | ❌ (rebuilt every step) |
| **Memory** | persistent, searchable, **cross-session** information | ✅ |

One-liner: **session = the box for one conversation; state = sticky-notes in the
box; context = the backpack you carry into the model this step; memory = what
passes between boxes.**

### 2.1 · Source vs product (the key distinction)

- The **session store** (state + full history) is the **static SOURCE** —
  append-only, unbounded. Memory is another source (from *other* boxes).
- **Context** is the **dynamic PRODUCT** — assembled each turn from those sources
  under a fixed window budget:
  `context ≈ instructions + state + selected history + retrieved memory`.

> The session store is the **warehouse**; context is what you **pack into the
> backpack** for this step. The backpack can't hold the warehouse — *how you pack
> it* is the discipline.

### 2.2 · Backends swap, concepts don't

All four are ADK **service interfaces**; only the implementation changes with
deployment:

| Primitive | Local backend | Managed backend |
|-----------|---------------|-----------------|
| Session / State | `session.db` (SQLite) | managed Sessions service |
| Memory | in-memory service | managed Memory Bank |
| Context | assembled model-side — **identical everywhere** | identical |

The same agent code runs local or hosted. **Cloud swaps the backend, not the
concept.**

---

## 3 · Context engineering

**Definition:** the transform **big static source → small sharp context**, under a
**hard window budget**. The difficulty *is* the budget: the source is unbounded,
the window is fixed, so you are forced to select and compress.

Context has **two layers**:

1. **Instruction / directional layer** — sets *what to care about and what to
   ignore*. Relatively fixed, injected up front. (e.g. system prompt, project
   config, skill definitions.)
2. **Data layer** — the real working data the agent **pulls on demand via tools**
   (read / search / query / memory-retrieval), sizing it itself.

That on-demand pull is why it is *agentic* context building (done at runtime by
the agent), as distinct from what a human pre-engineers at build time.

### 3.1 · Purpose is the compass

"Relevant" is never absolute — always *relevant-to-a-goal*. The agent's
**purpose** is the selection function that gives the transform a direction.

- **General agent** — direction is injected dynamically by each user prompt.
- **Purpose-built agent** — direction is baked into its instructions, so
  retrieval, domain memory, and ignore-rules can be pre-engineered.

> **Rule:** the narrower and more fixed the purpose, the sharper the relevance
> filter, the easier context engineering becomes. A narrow worker's context is
> nearly trivial; a wide, long-running coordinator is where it bites.

---

## 4 · The three-layer stack

Place any product on exactly one layer (compare within a layer, never across):

```
┌──────────────────────────────────────────────────────────┐
│ 3 · Operation Platform   host · multi-tenant · govern · monitor │  Gemini Enterprise
│                          · registry / discovery                 │  Agent Platform,
│                                                                 │  AWS Bedrock Agents,
│                                                                 │  Azure AI Foundry
├──────────────────────────────────────────────────────────┤
│ 2 · Framework            builds the harness around the loop;    │  ADK, OpenHands,
│                          you WRITE the agent here               │  Hermes, LangChain
├──────────────────────────────────────────────────────────┤
│ 1 · Model                the combustion source; called via API  │  Claude, Gemini, GPT
└──────────────────────────────────────────────────────────┘
```

You **write** at layer 2, **call** layer 1, and **deploy to** layer 3. A
"framework" (ADK, OpenHands, a homegrown harness) is just packaging of the §1
loop — no one reinvents the model or the loop; they re-package the harness.

---

## 5 · Two deployment archetypes = same engine, different axis

The loop is one point in a design space with these axes; the two mainstream
archetypes push opposite ones to the extreme.

| Axis | Enterprise platform (SaaS) | Digital employee (long-running) |
|------|----------------------------|---------------------------------|
| **Time horizon** | short: request → seconds/minutes → respond | long: one task runs hours→days |
| **Execution substrate** | managed, **stateless** compute; state externalized | **owns a computer** (container / VM: filesystem, shell) |
| **Fan-out** | **many tenants**, thousands of short concurrent sessions | **few, deep** — one agent owns an environment end-to-end |

How the four primitives stress differently in the long-running extreme:

- **Session** — blurs into a whole *work episode* of thousands of steps.
- **State** — the **filesystem itself becomes state**; checkpointing matters
  (resume after a crash).
- **Context** — the make-or-break problem: thousands of steps can't fit, so
  aggressive summarize / compact / retrieve is mandatory.
- **Memory** — the agent's own working notebook ("what I tried, what worked").

> Same four-stroke engine. The SaaS archetype pushes **multi-tenant identity**;
> the digital-employee archetype pushes **long horizon + an owned environment**.

---

## 6 · Capstone — two philosophies of the same engine

By 2026 both archetypes ship long-running operation and cross-session memory, so
the contrast is no longer *capability* — it is **architectural philosophy**.

> **Self-hosted digital employee = personal sovereignty** (my agent, my box, my
> data). **Enterprise platform = organizational control** (the org's agents, the
> org's guardrails, org-wide audit).

Grounded in two current systems — **Hermes Agent** (Nous Research, open-source,
self-hosted) vs **Gemini Enterprise Agent Platform** (Google, managed,
multi-tenant):

| First principle | Hermes Agent (digital employee · self-hosted) | Gemini Enterprise (SaaS · multi-tenant) |
|-----------------|-----------------------------------------------|-----------------------------------------|
| **Harness / loop** | ReAct + a closed **learning loop** (autonomous skill creation & self-improvement) | ReAct + managed Agent Runtime (**long-running up to 7 days**) |
| **Execution substrate** | **your own box** — 6 backends (local/Docker/SSH/Daytona/Singularity/Modal), hibernates when idle | managed cloud runtime, elastic scale |
| **Identity / tenancy** | **single-user** — models *who you are* | **multi-tenant** — per end-customer, at scale |
| **Memory** | **FTS5 cross-session recall + LLM summarization**; Honcho dialectic user modeling; stored **on your machine** | **Memory Bank** — managed, auto-provisioned, cloud, per-user |
| **Context engineering** | transparent — you can see the recall + summarize step | managed / opaque — "just works" |
| **Skills / tools** | **self-created, self-improving skills**; `agentskills.io` open standard + shareable Skills Hub; MCP for tools | tool connectors + **Gateways** for controlled connectivity |
| **Governance** | **inward / personal**: command approval, authorization, container isolation | **outward / organizational**: Agent Registry · Policies · Gateways · Security · runtime **SGP** |
| **Data sovereignty** | open-source (MIT), data never leaves the machine, no telemetry | data in the cloud, org-controlled, auditable |

Three axes worth internalizing:

- **Governance direction (see §7).** Hermes builds governance *into* the agent
  (self-enforced, single trust domain). Gemini enforces it *around* all agents at
  the platform boundary (non-bypassable, audited).
- **Context transparency.** Both hit the long-horizon window problem; Hermes is
  transparent (visible FTS5 recall + summarization), Gemini is managed/opaque.
  The eternal self-hosted-vs-managed trade-off: *control vs convenience*.
- **Memory subject.** Same M3 concept, opposite direction — Hermes builds one
  deep model of the single owner; Gemini builds per-customer memory across many
  tenants. **Depth vs breadth.**

---

## 7 · Governance — placement, not a pipeline

A common misconception is "the app *does*, the platform *manages*." **Wrong** —
both layers *do*. The correct frame is that the **same control** can sit at
different layers; you **place** it.

| Placement | Covers | Travels with the agent? | Exists when |
|-----------|--------|-------------------------|-------------|
| **In-agent** (e.g. Hermes command approval, a PII redaction step in code) | only this agent | ✅ everywhere (even off-platform) | always |
| **Platform** (e.g. Gemini Policies / SGP) | all agents uniformly | ❌ only on that platform | only while hosted there |

**When both apply — overlap and override are asymmetric:**

- By default controls **stack** (both run). For a guardrail that's harmless
  redundancy (defense in depth); for tracing it's duplicate signal to de-dup.
- A platform-mandatory control is a **floor** the agent **cannot go below** and
  **cannot opt out of**. The agent may add **stricter** controls on top, but
  **never looser** ones.

Consequence:

- **In-agent governance** = *by construction* — this one agent is safe **if** its
  author did it right, and it stays safe off-platform.
- **Platform governance** = *by policy* — the org is safe **even if** some author
  didn't, because you cannot trust every agent to self-enforce at scale.

> Analogy: a seatbelt you install in your own car (in-agent) vs a highway toll
> gate that inspects **every** car, including the careless ones (platform).
> Governance is not invented by the platform; the platform **industrializes** it
> — mandatory, centralized, non-bypassable, cross-agent, audited.

Runtime example of the platform extreme: **Semantic Governance Policies (SGP)**
evaluate each proposed tool call against user intent *and* organizational rules at
runtime — the same idea as a hand-written PII guardrail, made an org-wide,
non-bypassable, semantic platform service.

---

## The whole picture in one chain

```
one loop (four-stroke engine)  =  ReAct / TAO
        │  variations = loop + a topping (Reflexion, Plan-Execute, ToT)
        ▼
four primitives  (session · state · context · memory ; source → product)
        │  context engineering = pack the backpack under a fixed budget
        ▼
three-layer stack  (Model → Framework → Platform)
        │
        ▼
two archetypes  (SaaS multi-tenant  ↔  digital-employee long-running)
        │  same engine, opposite axis
        ▼
two philosophies  (sovereignty / transparency  ↔  control / scale)
        │
        ▼
governance  =  a placement decision (in-agent ↔ platform),
               stacking + a platform floor
```

Frameworks and products change weekly; the engine does not. Hold the loop, and
any new system — however recent — reduces to *which axis it pushes, what it added
on top of the loop, and where it places governance*.

---

### Sources

- Hermes Agent — Nous Research: <https://hermes-agent.nousresearch.com/> ·
  docs <https://hermes-agent.nousresearch.com/docs/>
- The new Gemini Enterprise — Google Cloud Blog:
  <https://cloud.google.com/blog/products/ai-machine-learning/the-new-gemini-enterprise-one-platform-for-agent-development>
- Gemini Enterprise Agent Platform — Agent Runtime & Memory:
  <https://medium.com/google-cloud/tutorial-series-gemini-enterprise-agent-platform-part-3-scaling-with-agent-runtime-memory-1fe9fe48d829>
- Securing the Agentic Era — Gemini Enterprise Agent Platform governance:
  <https://security.googlecloudcommunity.com/security-command-center-4/securing-the-agentic-era-new-gemini-enterprise-agent-platform-7376>
- ReAct: Synergizing Reasoning and Acting in Language Models (Yao et al., 2022):
  <https://arxiv.org/abs/2210.03629>
