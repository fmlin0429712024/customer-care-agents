# Customer Care Agent — Coordinator (to build)

The **conversational coordinator** that sits upstream of the specialist workers.
It talks to the customer over a long, multi-turn session and **routes** each
request to the right specialist — starting with the [refund worker](../refund-agent/).

This folder is a **skeleton**. It grows one milestone at a time (see the
workspace [`CLAUDE.md`](../CLAUDE.md) and the blueprint artifact).

## What makes this agent different from the refund worker

| | Refund worker (`../refund-agent`) | This coordinator |
|---|---|---|
| Session | short, one-shot (~30s) | long, multi-turn |
| Memory | unused | **needed** (remember the customer) |
| Context management | ignorable | **key** (long conversations) |
| Job | do one task end-to-end | understand intent, route, hold the conversation |
| Orchestration | `SequentialAgent` (fixed order) | `LLM-routed` (dynamic) |

## Build order

1. **M1** — routing concept (skill: [`../.claude/skills/customer-care/`](../.claude/skills/customer-care/)).
2. **M2** — ADK coordinator; refund worker as an in-process `sub_agent`.
3. **M3** — Memory Bank (cross-conversation memory).
4. **M4** — context management (summarize / retrieve for long chats).
5. **M5** — call the refund worker remotely via the **A2A protocol**.
6. **M6** — register to Gemini Enterprise.

## Prototype-first in Claude Code

The routing + persona can be prototyped fast as a Claude Code skill (same
`skills → ADK` path the refund worker took). Note: Claude Code **hides** memory
and context (its own memory files + compaction stand in). The **explicit**
learning of Memory Bank and context management happens when this moves to ADK
(M3 / M4).
