---
name: refund-policy
description: >
  Defines the refund eligibility rules — timeline window, amount cap, and
  delivery status requirements. Reference this to explain policy to a
  customer or to check a specific rule; use refund-decision to actually
  apply the full decision tree to an order.
status: development
version: 0.1.0
parent: customer-refund
---

# Refund Policy Rules

## Policy Overview
This skill defines the refund eligibility criteria for the customer
service pipeline. It is the rulebook; `refund-decision` is the engine
that applies it.

## Refund Eligibility Criteria

### Timeline-Based Rules
- **Days Since Delivery ≤ 5**: ✅ Eligible for automatic refund
- **Days Since Delivery > 5**: ❌ Requires human review (escalate)
- **Status = In Transit**: ❌ Cannot refund while in transit (escalate)
- **Status = Not Found**: ❌ Order does not exist (notify customer)

### Amount-Based Rules
- **Amount ≤ $500**: ✅ Can be auto-approved (if timeline allows)
- **Amount > $500**: ❌ High-value order (escalate to human)

## Processing Rules

### Auto-Approval Cases
- Must have all of: order found, delivered, ≤5 days, ≤$500
- Refund method: Original payment method
- Timeline: Process within 1 business day
- Notification: Auto-send confirmation email

### Escalation Cases
- Assign to human agent queue (see `escalation-rules/SKILL.md`)
- Priority: HIGH (if >3 days) or NORMAL (if ≤3 days)
- Timeout: 24 hours for human review
- Notification: Acknowledge customer, provide ticket number

### Rejection Cases
- Order not found: Suggest customer verify order number
- In transit: Explain cannot refund mid-shipping
- Send rejection reason via customer communication channel

## Special Cases

### Partial Refund
- Allowed with human approval only
- Document reason for partial amount

### Refund Status Inquiry
- Customers can track refund with order ID
- Show estimated processing time based on status

### Duplicate Refund Prevention
- Check if same order already has active refund
- Prevent multiple refunds for same order within 30 days
- See `fraud-detection/SKILL.md` for the detection logic

## Related Skills

- `refund-decision/SKILL.md` — applies these rules to a specific order
- `escalation-rules/SKILL.md` — what happens when a rule is violated
- `fraud-detection/SKILL.md` — abuse pattern screening before auto-approval
