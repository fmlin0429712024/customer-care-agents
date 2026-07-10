---
name: escalation-rules
description: >
  Defines the specific triggers, priorities, and reason codes for
  escalating a refund to a human agent. Run this after refund-decision
  returns ESCALATE, to determine priority and routing category before
  handing off to escalation-workflow for ticket creation.
status: development
version: 0.1.0
parent: customer-refund
---

# Escalation Rules

## Purpose
Define when and why a refund request escalates to a human agent, and at
what priority. `escalation-workflow` consumes this skill's output to
actually create and route the ticket.

## Escalation Triggers

### 1. Timeline Violation
- **Trigger**: Order delivered more than 5 days ago
- **Priority**: NORMAL
- **Reason Code**: `PAST_WINDOW`
- **Queue**: `REFUND_REVIEW`

### 2. High-Value Order
- **Trigger**: Refund amount > $500
- **Priority**: HIGH
- **Reason Code**: `HIGH_VALUE`
- **Queue**: `SENIOR_REFUND`

### 3. In-Transit Order
- **Trigger**: Order status is "in_transit"
- **Priority**: HIGH
- **Reason Code**: `IN_TRANSIT`
- **Queue**: `GENERAL_SUPPORT`
- **Message**: "Your order is still being delivered. Please allow more
  time or contact us once it arrives."

### 4. Order Not Found
- **Trigger**: Order ID does not exist in system
- **Priority**: NORMAL
- **Reason Code**: `NOT_FOUND`
- **Action**: Customer self-service → verify order number, contact
  support. This is a REJECT, not an escalation — no ticket needed unless
  the customer disputes it.

### 5. Duplicate Refund Request
- **Trigger**: Same order has an active or recent refund (see
  `fraud-detection/SKILL.md`)
- **Priority**: HIGH
- **Reason Code**: `DUPLICATE_REFUND`
- **Queue**: `FRAUD_TEAM`

### 6. Unusual Pattern (Refund Abuse)
- **Trigger**: Customer has >3 refunds in 30 days (see
  `fraud-detection/SKILL.md`)
- **Priority**: HIGH
- **Reason Code**: `FRAUD_RISK`
- **Queue**: `FRAUD_TEAM`

## Reason Code → Queue → Priority Map

| Reason Code | Queue | Priority | SLA Response |
|--------------|-------|----------|---------------|
| `PAST_WINDOW` | REFUND_REVIEW | NORMAL | 4 hours |
| `HIGH_VALUE` | SENIOR_REFUND | HIGH | 1 hour |
| `IN_TRANSIT` | GENERAL_SUPPORT | HIGH | 1 hour |
| `DUPLICATE_REFUND` | FRAUD_TEAM | HIGH | 1 hour |
| `FRAUD_RISK` | FRAUD_TEAM | HIGH | 1 hour |
| `UNKNOWN_STATUS` | GENERAL_SUPPORT | NORMAL | 4 hours |

## De-escalation Conditions

Return to auto-processing only if new data resolves the trigger — e.g.
corrected delivery date shows the order is actually within the 5-day
window. Re-run `refund-decision` from scratch; do not manually override.

## Related Skills

- `refund-decision/SKILL.md` — determines that ESCALATE is the outcome
- `escalation-workflow/SKILL.md` — creates the ticket and manages SLA
- `fraud-detection/SKILL.md` — supplies the duplicate/pattern signals
