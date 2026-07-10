# Testing Cheat Sheet

A copy-paste prompt list for manually testing the `customer-refund` skill
in Claude Code. Intended for business users / QA who don't need to read
the skill files themselves — just type the prompt, compare the result to
"Expected."

## How to Test

1. Open this project folder in Claude Code.
2. Copy a prompt from below into the chat.
3. Compare Claude's response to the **Expected** row.
4. Report any mismatch as a bug (reference the scenario ID).

Source of truth for these scenarios: `.claude/skills/customer-refund/reference/test-scenarios.json`

---

## Scenario 1 — Happy Path: Auto-Approve ✅

**Prompt:**
```
Process a refund request for order 67890
```

**Expected:**
| Field | Value |
|---|---|
| Decision | APPROVE |
| Reason | AUTO_APPROVED |
| Amount | $49.00 |
| Message mentions | original payment method, 1 business day |

---

## Scenario 2 — Escalate: Past Refund Window 👤

**Prompt:**
```
Process a refund request for order 12345
```

**Expected:**
| Field | Value |
|---|---|
| Decision | ESCALATE |
| Reason | PAST_REFUND_WINDOW |
| Priority | NORMAL |
| Message mentions | ticket number, ~4 hour response SLA, "delivered 7 days ago" |

---

## Scenario 3 — Escalate: Still In Transit 👤

**Prompt:**
```
Process a refund request for order 11111
```

**Expected:**
| Field | Value |
|---|---|
| Decision | ESCALATE |
| Reason | IN_TRANSIT |
| Priority | HIGH |
| Message mentions | order hasn't arrived yet, refund possible after delivery |

---

## Scenario 4 — Reject: Order Not Found ❌

**Prompt:**
```
Process a refund request for order 99999
```

**Expected:**
| Field | Value |
|---|---|
| Decision | REJECT |
| Reason | ORDER_NOT_FOUND |
| Message mentions | asks customer to double-check the order number |

---

## Scenario 5 — Escalate: High-Value Order 👤

Not in `orders.json` by default — describe the order directly in the prompt so you can test the $500 cap on its own, independent of the timeline rule.

**Prompt:**
```
Process a refund request for order HIGH001: $750, delivered 2 days ago.
```

**Expected:**
| Field | Value |
|---|---|
| Decision | ESCALATE |
| Reason | HIGH_VALUE_ORDER |
| Priority | HIGH |
| Message mentions | amount exceeds auto-refund limit, routed to senior agent |

---

## Scenario 6 — Escalate: Duplicate Refund Detected 👤

Same order as Scenario 1, but with a fraud signal added inline (there's already an open ticket).

**Prompt:**
```
Process a refund request for order 67890 ($49, delivered 2 days ago).
Note: this order already has an open refund ticket (ESCA-20260701000000-EXAMPLE)
from last week — check for duplicates before approving.
```

**Expected:**
| Field | Value |
|---|---|
| Decision | ESCALATE (overrides the tentative APPROVE) |
| Reason | DUPLICATE_REFUND |
| Priority | HIGH |
| Message mentions | verification team, non-accusatory tone |

---

## Scenario 7 — Escalate: Refund Frequency Abuse 👤

Same order as Scenario 1, but the customer has refunded too often recently.

**Prompt:**
```
Process a refund request for order 67890 ($49, delivered 2 days ago).
Note: this customer has already had 4 refunds in the past 30 days.
```

**Expected:**
| Field | Value |
|---|---|
| Decision | ESCALATE (overrides the tentative APPROVE) |
| Reason | FRAUD_RISK |
| Priority | HIGH |
| Message mentions | verification team, non-accusatory tone |

---

## Regression Pass (all 7 at once)

For a quick full-suite check, paste:

```
Run all 7 test scenarios in .claude/skills/customer-refund/reference/test-scenarios.json.
For each, report: scenario ID, actual decision, actual reason code, and whether
it matches the expected_decision / expected_reason in the file. Summarize
pass/fail at the end.
```

---

## Adding a New Test Case

To make a new scenario repeatable (not just a one-off prompt):

1. Add the order to `.claude/skills/customer-refund/reference/orders.json`.
2. Add the expected outcome to `.claude/skills/customer-refund/reference/test-scenarios.json`.
3. Add a row to this file so it's discoverable during manual testing.

## Result Legend

| Symbol | Meaning |
|---|---|
| ✅ | Auto-resolved, no human involved |
| 👤 | Escalated — a human agent must act |
| ❌ | Rejected — customer needs to self-correct |
