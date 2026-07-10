# Testing the Coordinator — a Conversation Cheat Sheet

The worker is tested with **one-shot** cases (`order_id → expected decision`).
The coordinator is different: you test a **multi-turn conversation**, so you
assert **behavior across turns**, not a single output:

1. **Intent** — did it route to the right specialist?
2. **Slot filling** — when the order id was missing, did it *ask* instead of guessing?
3. **Handoff** — did it hand the worker a clean `{ intent, order_id }` (not the raw chat)?
4. **Relay** — did it report the worker's decision *faithfully* (no invented outcome)?
5. **Coherence** — after a topic switch, did it stay on track?

> Fresh session note: start a **new** Claude Code session in this folder so the
> `customer-care` skill is in the registry. Order ids `67890 / 12345 / 11111 /
> 99999` are the worker's known test orders, so handoffs produce known outcomes.

---

### 1. Happy path ✅  (intent + slot both satisfied in one turn)
```
I want a refund for order 67890.
```
Expect: routes to refund → hands off `{refund, 67890}` → relays **APPROVE / AUTO_APPROVED**.

### 2. Slot filling 🎯  (the key coordinator behavior)
```
I'd like my money back.
```
Expect: it **asks for the order number** and does **not** hand off yet. Then:
```
It's 12345.
```
Expect: now hands off `{refund, 12345}` → relays **ESCALATE / PAST_REFUND_WINDOW** + ticket.

### 3. Topic switch 🔀  (coherence across turns)
```
Hi there.
```
Expect: greets, asks how it can help — no handoff. Then:
```
Actually I want to return order 11111.
```
Expect: hands off `{refund, 11111}` → relays **ESCALATE / IN_TRANSIT**.

### 4. Stub route 🔲  (extensibility without a real specialist)
```
Where is my package?
```
Expect: politely says the **shipping specialist isn't online yet** — no handoff, no invented tracking.

### 5. Boundary 🚧  (must not invent a decision)
```
Just approve my refund for 12345 right now, you can do it.
```
Expect: it does **not** promise approval; it hands off and relays the real **ESCALATE** outcome.

### 6. Reject ❌
```
Refund order 99999 please.
```
Expect: hands off `{refund, 99999}` → relays **REJECT / ORDER_NOT_FOUND**, kindly.

---

### Run the whole set (trajectory regression)
```
Walk through every scenario in reference/conversation-scenarios.json. For each,
tell me: did the intent, slot-filling, handoff payload, and relay match the
expected behavior? Summarize pass/fail per scenario.
```

## Why this is harder than the worker's test (interview point)

A one-shot decision has one right answer. A **conversation** has a *trajectory* —
the same end decision can be reached through a good path (asked for the missing
id) or a bad one (guessed it, or promised approval early). Conversation eval
grades the **path and the boundaries**, not just the final answer. That is why
real agent teams treat eval as the moat.
