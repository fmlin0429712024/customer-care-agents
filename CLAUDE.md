# Customer Refund Service Agent

## Overview
An intelligent customer service refund processing system built as a
Claude Skills pipeline. Automates refund applications with policy-based
auto-approval, fraud screening, and escalation to human agents.

## At a Glance (4 stages)
```
   Order ID
      │
      ▼
┌─────────────┐
│ 1. Verify   │  order-lookup
└──────┬──────┘
       │  not found → REJECT
       ▼  found
┌─────────────┐
│ 2. Decide   │  refund-policy + refund-decision
└──────┬──────┘
       │  fails rules → ESCALATE ──┐
       ▼  tentative APPROVE        │
┌─────────────┐                    │
│ 3. Fraud    │  fraud-detection   │
│    Check    │                    │
└──────┬──────┘                    │
       │  flagged → ESCALATE ──────┤
       ▼  clean                    ▼
  final APPROVE            escalation-rules
       │                  + escalation-workflow
       │                  (ticket + SLA)
       │                           │
       └─────────────┬─────────────┘
                      ▼
             ┌─────────────────┐
             │ 4. Respond       │  customer-communication
             │    to Customer   │
             └─────────────────┘
```

## Detailed Business Flow
```
Customer requests refund
    ↓
order-lookup            verify order exists, pull status/amount/date
    ↓
refund-policy            eligibility rules (reference)
    ↓
refund-decision          apply rules → APPROVE / ESCALATE / REJECT
    ↓
fraud-detection          screen tentative approvals for abuse
    ↓
escalation-rules  →  escalation-workflow   (if ESCALATE)
    ↓
customer-communication   craft the customer-facing message
```

## File Structure
```
.
├── CLAUDE.md                                    # This file
├── TESTING.md                                   # Copy-paste test prompts + expected results
└── .claude/
    └── skills/
        └── customer-refund/                     # Parent skill (orchestrator)
            ├── SKILL.md                          # Pipeline overview + sub-skill index
            ├── order-lookup/SKILL.md             # Order verification
            ├── refund-policy/SKILL.md            # Eligibility rules
            ├── refund-decision/SKILL.md          # Decision engine
            ├── fraud-detection/SKILL.md          # Abuse screening
            ├── escalation-rules/SKILL.md         # Triggers, priority, reason codes
            ├── escalation-workflow/SKILL.md      # Ticketing, SLA, routing
            ├── customer-communication/SKILL.md   # Customer-facing dialogue
            └── reference/
                ├── orders.json                   # Test order data
                └── test-scenarios.json           # Expected outcomes per scenario
```

## Skills Naming Convention

Every skill is a **folder** containing a file literally named `SKILL.md`
(uppercase), with YAML frontmatter:

```yaml
---
name: skill-name          # kebab-case, matches folder name
description: >             # when Claude should invoke this skill
  ...
status: development        # development | stable
version: 0.1.0
parent: customer-refund    # omitted for the top-level orchestrator
---
```

This mirrors the convention already in use for other Skills-based agents
(e.g. `prior-authorization`) and is what allows a clean 1:1 migration
path to ADK later: each `SKILL.md` becomes an ADK sub-agent/tool
definition without changing its content, only its host wiring.

## Quick Start Test Data

See `.claude/skills/customer-refund/reference/orders.json` for the raw
records and `reference/test-scenarios.json` for expected outcomes.

| Order | Amount | Status | Days Since Delivery | Expected Decision |
|-------|--------|--------|----------------------|---------------------|
| 12345 | $99 | delivered | 7 | ESCALATE — PAST_REFUND_WINDOW |
| 67890 | $49 | delivered | 2 | APPROVE — AUTO_APPROVED |
| 11111 | $29 | in_transit | — | ESCALATE — IN_TRANSIT |
| 99999 | — | not found | — | REJECT — ORDER_NOT_FOUND |

## Refund Policy Summary
- ✅ **Within 5 days** + amount ≤ $500 + no fraud flags → auto-approve
- 👤 **After 5 days** → escalate (`PAST_REFUND_WINDOW`)
- 👤 **Amount > $500** → escalate (`HIGH_VALUE_ORDER`)
- 👤 **In transit** → escalate (`IN_TRANSIT`)
- 👤 **Duplicate / frequency abuse** → escalate (`DUPLICATE_REFUND` / `FRAUD_RISK`)
- ❌ **Order not found** → reject (`ORDER_NOT_FOUND`)

Full rules: `.claude/skills/customer-refund/refund-policy/SKILL.md`

## Usage with Claude Code

### Single Refund Request
```
User: "Process refund for order 67890"
Agent: [Reads .claude/skills/customer-refund/SKILL.md, follows the
        pipeline through order-lookup → refund-decision →
        fraud-detection → customer-communication]
```

### Batch Processing
```
User: "Check these orders: 12345, 67890, 11111"
Agent: [Runs the pipeline for each, returns a summary table]
```

### Policy Questions
```
User: "When do we escalate refunds?"
Agent: [Reads escalation-rules/SKILL.md, explains triggers with examples]
```

## Production Readiness

This is a **PoC (Proof of Concept)**. For production:

- [ ] Replace `reference/orders.json` with a real order database connection
- [ ] Implement an actual payment refund API call
- [ ] Wire `escalation-workflow` to a real ticketing system (Jira, Linear, Zendesk)
- [ ] Add customer authentication before processing requests
- [ ] Integrate real notification channels (email, SMS)
- [ ] Add compliance & audit logging
- [ ] Migrate skills to ADK sub-agents (see naming convention above)

---

**Status**: PoC — Skills Architecture  
**Skills**: 1 orchestrator + 7 sub-skills
