"""Business logic and rules embedded as constants — fully self-contained."""

# ============================================================================
# REFUND POLICY RULES
# ============================================================================

REFUND_POLICY = """
## Refund Eligibility Rules

### Timeline-Based Rules
- Days Since Delivery ≤ 5: ✅ Eligible for automatic refund
- Days Since Delivery > 5: ❌ Requires human review (escalate)
- Status = In Transit: ❌ Cannot refund while in transit (escalate)
- Status = Not Found: ❌ Order does not exist (notify customer)

### Amount-Based Rules
- Amount ≤ $500: ✅ Can be auto-approved (if timeline allows)
- Amount > $500: ❌ High-value order (escalate to human)

### Auto-Approval Cases
Must have all of: order found, delivered, ≤5 days, ≤$500, no fraud flags
→ Refund method: Original payment method
→ Timeline: Process within 1 business day

### Escalation Cases
Assign to human agent queue with priority based on reason:
- PAST_WINDOW: NORMAL priority (4 hour SLA)
- HIGH_VALUE: HIGH priority (1 hour SLA)
- IN_TRANSIT: HIGH priority (1 hour SLA)
- DUPLICATE_REFUND: HIGH priority (1 hour SLA)
- FRAUD_RISK: HIGH priority (1 hour SLA)
"""

# ============================================================================
# REFUND DECISION ENGINE
# ============================================================================

REFUND_DECISION_LOGIC = """
## Refund Decision Tree

Apply in this exact order — first match wins:

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

---

Output format:
- Decision: APPROVE | ESCALATE | REJECT
- Reason Code: [reason from above]
- Priority: HIGH | NORMAL | N/A
- Message: [one-line human-readable explanation]
"""

# ============================================================================
# FRAUD DETECTION RULES
# ============================================================================

FRAUD_DETECTION_LOGIC = """
## Fraud Screening — Pre-Finalization Checks

Before auto-approving, screen for abuse patterns:

### Check 1: Duplicate Refund on Same Order
- Trigger: This order already has an OPEN or COMPLETED refund ticket within 30 days
- Result: Downgrade decision to ESCALATE
- Reason Code: DUPLICATE_REFUND
- Priority: HIGH

### Check 2: Refund Frequency Abuse
- Trigger: Same customer has more than 3 refunds (approved or escalated) in trailing 30 days
- Result: Downgrade decision to ESCALATE
- Reason Code: FRAUD_RISK
- Priority: HIGH

### Check 3: Clean Pass
- Trigger: Neither check above fires
- Result: Confirm the tentative APPROVE — refund proceeds

---

Decision Logic:
IF duplicate_refund_on_order THEN
  → ESCALATE (override tentative APPROVE)
  → reason: DUPLICATE_REFUND

ELSE IF customer_refund_count_30d > 3 THEN
  → ESCALATE (override tentative APPROVE)
  → reason: FRAUD_RISK

ELSE
  → CONFIRM APPROVE
"""

# ============================================================================
# CUSTOMER COMMUNICATION TEMPLATES
# ============================================================================

COMMUNICATION_TEMPLATES = {
    "approve": """🎉 **REFUND APPROVED**

Order #{order_id} — ${amount:.2f} refund approved for immediate processing.

Your refund will be returned to your original payment method within 1 business day.
You'll receive a confirmation email shortly with the details.

---

**Summary:**
- Decision: ✅ APPROVE
- Amount: ${amount:.2f}
- Processing: 1 business day
- Refund method: Original payment method
""",

    "escalate_past_window": """👤 **ESCALATED TO HUMAN REVIEW**

Thank you for your refund request for Order #{order_id} (${amount:.2f}, delivered {days} days ago).

Your order was delivered outside our standard 5-day refund window. I'm escalating your case
to our refund review team for consideration.

**Ticket Number:** {ticket_id}
**Priority:** Normal
**Expected Response:** Within 4 hours

A specialist will review your request and contact you with a decision.

---

**Summary:**
- Decision: 👤 ESCALATE
- Reason: PAST_REFUND_WINDOW
- SLA: 4 hours response
""",

    "escalate_high_value": """👤 **ESCALATED TO SENIOR AGENT**

Thank you for your refund request for your ${amount:.2f} order (delivered {days} days ago).

Your order amount exceeds our standard auto-approval limit. I'm routing your request to
our senior refund team for personalized review.

**Ticket Number:** {ticket_id}
**Priority:** High
**Expected Response:** Within 1 hour

A senior agent will review your case and contact you shortly.

---

**Summary:**
- Decision: 👤 ESCALATE
- Reason: HIGH_VALUE_ORDER
- SLA: 1 hour response
""",

    "escalate_in_transit": """👤 **ESCALATED — ORDER IN TRANSIT**

Thank you for your refund request for Order #{order_id} (${amount:.2f}).

Your order is currently in transit and hasn't arrived yet. We'll be able to process
a refund once it's been delivered.

**Two options:**
1. Wait for delivery and request a refund after it arrives
2. Contact us now with Ticket: {ticket_id}

Our team will contact you within 1 hour if you'd like to proceed now.

---

**Summary:**
- Decision: 👤 ESCALATE
- Reason: IN_TRANSIT
- SLA: 1 hour response
""",

    "escalate_duplicate": """👤 **ESCALATED — VERIFICATION NEEDED**

Thank you for your refund request for Order #{order_id} (${amount:.2f}).

We've detected that this order already has a recent refund request in our system.
To prevent duplicate processing and protect your account, we're connecting you
with our verification team.

**Ticket Number:** {ticket_id}
**Priority:** High
**Expected Response:** Within 1 hour

Our team will reach out shortly to clarify and complete your request.

---

**Summary:**
- Decision: 👤 ESCALATE
- Reason: DUPLICATE_REFUND
- SLA: 1 hour response
""",

    "escalate_fraud_risk": """👤 **ESCALATED — VERIFICATION NEEDED**

Thank you for your refund request for Order #{order_id} (${amount:.2f}).

As part of our standard verification process for multiple refund requests,
we need to connect you with our verification team. This protects both you
and our platform.

**Ticket Number:** {ticket_id}
**Priority:** High
**Expected Response:** Within 1 hour

A specialist will review your account and reach out shortly.

---

**Summary:**
- Decision: 👤 ESCALATE
- Reason: FRAUD_RISK
- SLA: 1 hour response
""",

    "reject_not_found": """❌ **ORDER NOT FOUND**

I couldn't find an order with ID {order_id} in our system.

**Please verify:**
- Is the order number correct? (Should be 5 digits)
- Check your order confirmation email for the exact order ID
- If you need help locating your order, please contact our support team

Once you have the correct order number, feel free to submit your refund
request again or reach out to us directly.

---

**Summary:**
- Decision: ❌ REJECT
- Reason: ORDER_NOT_FOUND
- Action: Customer self-service
""",
}
