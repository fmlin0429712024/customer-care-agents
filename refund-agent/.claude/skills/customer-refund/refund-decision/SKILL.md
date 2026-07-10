---
name: refund-decision
description: >
  Applies the refund-policy rules to a specific order and returns a single
  decision: APPROVE, ESCALATE, or REJECT. Run this after order-lookup and
  before fraud-detection. This is the deterministic engine — it does not
  redefine policy, it only executes it.
status: development
version: 0.1.0
parent: customer-refund
---

# Refund Decision Engine

You are the adjudicator in the refund pipeline. Given order details from
`order-lookup`, apply the rules from `refund-policy/SKILL.md` and return
exactly one decision.

## Input

Order details from `order-lookup`:
- `order_id`, `status`, `amount`, `days_since_delivery` (or null)

## Decision Logic

Apply in this exact order — first match wins:

```
IF order not found THEN
  → REJECT
  → reason: ORDER_NOT_FOUND

ELSE IF status == "in_transit" THEN
  → ESCALATE
  → reason: IN_TRANSIT
  → priority: HIGH

ELSE IF status == "delivered" AND days_since_delivery > 5 THEN
  → ESCALATE
  → reason: PAST_REFUND_WINDOW
  → priority: NORMAL

ELSE IF status == "delivered" AND amount > 500 THEN
  → ESCALATE
  → reason: HIGH_VALUE_ORDER
  → priority: HIGH

ELSE IF status == "delivered" AND days_since_delivery <= 5 AND amount <= 500 THEN
  → proceed to fraud-detection before final APPROVE
  → tentative reason: AUTO_APPROVED

ELSE
  → ESCALATE
  → reason: UNKNOWN_STATUS
  → priority: NORMAL
```

## Output Format

```
=== REFUND DECISION ===
Order ID:     [order_id]
Decision:     APPROVE | ESCALATE | REJECT
Reason:       [reason code]
Priority:     [HIGH | NORMAL | N/A]
Message:      [one-line human-readable explanation]

NEXT STEP: [fraud-detection (if tentative APPROVE) | escalation-rules | customer-communication]
```

## Worked Examples (from `reference/test-scenarios.json`)

| Order | Status | Days | Amount | Decision | Reason |
|-------|--------|------|--------|----------|--------|
| 12345 | delivered | 7 | $99 | ESCALATE | PAST_REFUND_WINDOW |
| 67890 | delivered | 2 | $49 | APPROVE (pending fraud check) | AUTO_APPROVED |
| 11111 | in_transit | — | $29 | ESCALATE | IN_TRANSIT |
| 99999 | — | — | — | REJECT | ORDER_NOT_FOUND |

## Rules

- This skill never talks to the customer directly — hand off the decision
  to `customer-communication` for messaging.
- A tentative APPROVE is not final until `fraud-detection` clears it.
- Do not skip steps in the decision order — checking amount before
  timeline (or vice versa) can produce the wrong reason code even if the
  final ESCALATE/APPROVE outcome happens to match.
