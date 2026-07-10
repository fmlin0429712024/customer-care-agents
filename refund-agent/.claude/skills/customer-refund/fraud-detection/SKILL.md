---
name: fraud-detection
description: >
  Screens a tentatively-approved refund for abuse patterns — duplicate
  requests on the same order, or excessive refund frequency for the same
  customer — before it is finalized. Run this after refund-decision
  returns a tentative APPROVE, and before customer-communication.
status: development
version: 0.1.0
parent: customer-refund
---

# Fraud Detection

You are the last gate before an auto-approved refund is finalized. Your
job is to catch abuse patterns that policy rules alone wouldn't flag.

## Input

- `order_id`, `customer_id` from the tentative APPROVE decision
- Customer's refund history (from `reference/orders.json` /
  `reference/test-scenarios.json`, or a real refund-history store in
  production)

## Checks

### 1. Duplicate Refund on Same Order
- **Trigger**: This order already has an OPEN or COMPLETED refund ticket
  within the last 30 days
- **Result**: Downgrade decision to ESCALATE
- **Reason Code**: `DUPLICATE_REFUND`
- **Priority**: HIGH → route to `FRAUD_TEAM`

### 2. Refund Frequency Abuse
- **Trigger**: Same customer has more than 3 refunds (approved or
  escalated) in the trailing 30 days
- **Result**: Downgrade decision to ESCALATE
- **Reason Code**: `FRAUD_RISK`
- **Priority**: HIGH → route to `FRAUD_TEAM`

### 3. Clean Pass
- **Trigger**: Neither check above fires
- **Result**: Confirm the tentative APPROVE — refund proceeds

## Decision Logic

```
IF duplicate_refund_on_order THEN
  → ESCALATE (override tentative APPROVE)
  → reason: DUPLICATE_REFUND

ELSE IF customer_refund_count_30d > 3 THEN
  → ESCALATE (override tentative APPROVE)
  → reason: FRAUD_RISK

ELSE
  → CONFIRM APPROVE
```

## Output Format

```
=== FRAUD SCREEN RESULT ===
Order ID:          [order_id]
Customer ID:        [customer_id]
Duplicate Check:    PASS | FAIL (existing ticket: [ticket_id])
Frequency Check:    PASS | FAIL (count: [N] in 30d)
Final Decision:     APPROVE (confirmed) | ESCALATE

NEXT STEP: [customer-communication | escalation-rules]
```

## Rules

- Never accuse a customer of fraud in customer-facing language — use
  neutral wording ("additional verification needed"). Accusatory tone is
  for the internal note only (see `escalation-workflow/SKILL.md`).
- This skill only screens orders that already passed policy (tentative
  APPROVE). Orders already headed to ESCALATE via `refund-decision` skip
  this check — they're getting human review regardless.
- Do not silently deny — every override must produce a reason code and
  route to a queue via `escalation-rules/SKILL.md`.

## Related Skills

- `refund-decision/SKILL.md` — supplies the tentative APPROVE this skill screens
- `escalation-rules/SKILL.md` — consumes `DUPLICATE_REFUND` / `FRAUD_RISK` reason codes
