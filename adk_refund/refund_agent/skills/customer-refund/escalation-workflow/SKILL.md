---
name: escalation-workflow
description: >
  Creates and routes an escalation ticket once escalation-rules has
  determined the reason code and priority. Handles ticket ID generation,
  queue assignment, SLA tracking, and the internal note for the human
  agent. Run this last in the escalation path, before customer-communication.
status: development
version: 0.1.0
parent: customer-refund
---

# Escalation Workflow

You are the ticketing and routing step. You do not decide *whether* to
escalate (that's `refund-decision` + `escalation-rules`) — you execute
the escalation once it's been decided.

## Input

From `escalation-rules`:
- `order_id`, `customer_id`, `amount`, `reason_code`, `priority`, `queue`

## Step-by-Step Process

### 1. Generate Ticket ID

Format: `ESCA-{YYYYMMDDHHMMSS}-{8-char-random}`

Example: `ESCA-20260709120000-A1B2C3D4`

### 2. Assemble Ticket Record

```
{
  "ticket_id": "...",
  "order_id": "...",
  "customer_id": "...",
  "amount": ...,
  "reason": "...",
  "priority": "HIGH | NORMAL",
  "status": "OPEN",
  "created_at": "<ISO timestamp>",
  "queue": "...",
  "sla_response_hours": 1 | 4,
  "sla_resolution_hours": 4 | 24
}
```

SLA by priority:

| Priority | Response SLA | Resolution SLA |
|----------|--------------|-----------------|
| HIGH | 1 hour | 4 hours |
| NORMAL | 4 hours | 24 hours |

### 3. Write Internal Note

Give the human agent the context they need without re-deriving it:

```
Escalation for order [order_id]
Reason: [reason_code]
Days since delivery: [N or N/A]
Amount: $[amount]
Prior refunds (if flagged by fraud-detection): [count]
```

### 4. Hand Off

- Ticket + internal note → human agent queue
- Reason code + ticket ID → `customer-communication` for the customer-facing message

## Agent Handling Guidelines (for the human agent picking up the ticket)

1. Review full order history.
2. Check customer refund history (fraud prevention).
3. Consider special circumstances: product quality issues, shipping
   damage, customer service failures.
4. Determine action: approve refund (even if out of window), offer
   alternative (exchange, credit), or deny with explanation.
5. Communicate the decision back through `customer-communication`.

## Approval Authority

| Case | Who can approve |
|------|-------------------|
| Standard refund | Any trained agent |
| High-value (>$500) | Senior agent or manager |
| Fraud suspected | Fraud team lead |
| Policy exception | Manager approval required |

## Monitoring

Track per escalation: reason code distribution, time-to-resolution by
priority, and agent handling time. Feed patterns back into
`refund-policy` if a reason code is escalating far more than expected —
that's a signal the auto-approval thresholds may need revisiting.

## Related Skills

- `escalation-rules/SKILL.md` — supplies reason_code, priority, queue
- `customer-communication/SKILL.md` — turns the ticket into a customer message
