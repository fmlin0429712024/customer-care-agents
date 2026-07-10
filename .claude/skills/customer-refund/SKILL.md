---
name: customer-refund
description: >
  AI-powered customer refund pipeline for e-commerce support. Orchestrates
  order lookup, policy evaluation, fraud screening, and escalation to
  auto-resolve routine refunds within a 5-day / $500 threshold while
  routing edge cases to human agents. Trigger on any refund-related
  request: order status, refund eligibility, refund processing, or
  escalation to a human agent.
status: development
version: 0.1.0
---

# Customer Refund — AI Pipeline Orchestrator

## What this skill does

Automates the customer service refund workflow through a single linear
pipeline: verify the order, decide eligibility, screen for fraud, then
either auto-approve or escalate.

```
Customer refund request
         │
         ▼
┌─────────────────────┐
│  order-lookup       │  ← verify order exists, get status/amount/date
└──────────┬──────────┘
           │ FOUND
           ▼
┌─────────────────────┐
│  refund-policy      │  ← eligibility rules (5-day window, $500 cap)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  refund-decision    │  ← apply rules → APPROVE / ESCALATE / REJECT
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  fraud-detection    │  ← check for abuse patterns before auto-approving
└──────────┬──────────┘
           │
    ┌──────┴──────┬──────────┐
    ▼             ▼          ▼
APPROVE        ESCALATE    REJECT
(auto)      (human agent)  (not found)
    │             │          │
    ▼             ▼          │
┌───────────┐ ┌──────────────┴──┐
│ customer- │ │ escalation-     │
│ communi-  │ │ workflow        │
│ cation     │ │ (ticket + SLA) │
└───────────┘ └─────────────────┘
```

## Sub-skills

| Sub-skill | Location | Invoke when... |
|-----------|----------|----------------|
| **Order Lookup** | `order-lookup/SKILL.md` | A refund request arrives — verify the order exists and pull status/amount/delivery date |
| **Refund Policy** | `refund-policy/SKILL.md` | Order confirmed — check eligibility rules (timeline, amount) |
| **Refund Decision** | `refund-decision/SKILL.md` | Policy checked — apply the decision tree to get APPROVE / ESCALATE / REJECT |
| **Fraud Detection** | `fraud-detection/SKILL.md` | Before auto-approving — screen for abuse patterns (repeat refunds, etc.) |
| **Escalation Rules** | `escalation-rules/SKILL.md` | Decision is ESCALATE — determine the specific trigger and priority |
| **Escalation Workflow** | `escalation-workflow/SKILL.md` | Escalation confirmed — create ticket, assign queue, set SLA |
| **Customer Communication** | `customer-communication/SKILL.md` | Any outcome reached — craft the customer-facing message |

## Reference data (this skill)

All reference data lives inside this skill directory — self-contained.

| File | Used by | Contents |
|------|---------|----------|
| `reference/orders.json` | order-lookup, refund-decision | Test order records: status, amount, delivery date |
| `reference/test-scenarios.json` | all sub-skills | End-to-end test cases with expected outcomes |

Sub-skills reference these as `reference/<file>.json` relative to this skill root
(`.claude/skills/customer-refund/reference/`).

## How to invoke a sub-skill

Read the relevant `SKILL.md` before starting:

```
# Full pipeline for a refund request:
Read .claude/skills/customer-refund/order-lookup/SKILL.md, then look up order 67890.

# Check eligibility once order details are known:
Read .claude/skills/customer-refund/refund-decision/SKILL.md, then decide on order 12345
($99, delivered 7 days ago).

# Escalate a case:
Read .claude/skills/customer-refund/escalation-workflow/SKILL.md, then create a ticket
for order 12345, reason PAST_WINDOW.

# Draft the customer-facing reply:
Read .claude/skills/customer-refund/customer-communication/SKILL.md, then write the
response for an ESCALATED case.
```

## Quick reference: decision thresholds

| Rule | Threshold | Outcome if violated |
|------|-----------|---------------------|
| Refund window | ≤ 5 days since delivery | ESCALATE (past window) |
| Auto-approval cap | ≤ $500 | ESCALATE (high value) |
| Delivery status | must be `delivered` | ESCALATE (in transit) |
| Order existence | must exist in system | REJECT (not found) |

## Agent roles

| Role | Layer | Responsibility |
|------|-------|-----------------|
| **Order Lookup** | Forward | Verifier — confirms order exists, never fabricates data |
| **Refund Decision** | Forward | Adjudicator — applies written policy, no judgment calls |
| **Fraud Detection** | Forward | Screener — flags patterns, never accuses without evidence |
| **Escalation Workflow** | Forward | Router — assigns queue/priority/SLA, doesn't decide outcome |
| **Customer Communication** | Forward | Communicator — tone and clarity, never invents policy |
| **Human agent** | HITL | Judgment call on escalated/ambiguous cases |

Ambiguous or high-value cases always go to a human agent. The AI auto-resolves
only cases where the criteria are fully deterministic.

## Business context

| Metric | Target |
|--------|--------|
| Auto-resolution rate | Orders ≤5 days, ≤$500 |
| Escalation SLA (high priority) | 1 hour response / 4 hour resolution |
| Escalation SLA (normal priority) | 4 hour response / 24 hour resolution |
