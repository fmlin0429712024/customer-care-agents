"""Customer Refund Agent Pipeline — Google ADK Implementation (Self-Contained)."""

from google.adk.agents import Agent, SequentialAgent
from refund_agent.skills import (
    REFUND_POLICY,
    REFUND_DECISION_LOGIC,
    FRAUD_DETECTION_LOGIC,
    COMMUNICATION_TEMPLATES,
)

MODEL = "gemini-2.5-pro"


# ---------------------------------------------------------------------------
# Stage 1: Order Lookup — Verify & Extract
# ---------------------------------------------------------------------------

def _build_order_lookup_agent() -> Agent:
    """Order lookup agent — verify order exists and extract details."""

    def get_instruction(ctx):
        order_id = ctx.state.get("order_id", "67890")
        reference_orders = ctx.state.get("reference_orders", "{}")
        return f"""You are the order verification step of the refund pipeline.

Your job is to confirm an order exists and extract the fields needed for eligibility evaluation.

Reference data (all orders in system):
{reference_orders}

---
## Order to Look Up

Order ID: {order_id}

---
## Your Task

1. Search the reference data for this order ID.
2. If found, extract these fields:
   - order_id
   - customer_id
   - amount
   - status (delivered | in_transit)
   - delivery_date (or null if not yet delivered)
   - product

3. If status == "delivered", calculate:
   days_since_delivery = today (2026-07-09) − delivery_date

4. Output format:

=== ORDER LOOKUP RESULT ===
Order ID:              [order_id]
Found:                 YES | NO
Customer ID:           [customer_id or N/A]
Status:                [delivered | in_transit | not_found]
Amount:                $[amount]
Delivery Date:         [date or "N/A — in transit"]
Days Since Delivery:   [N or "N/A"]
Product:               [product]

NEXT STEP: refund-policy evaluation

---

Do NOT guess or infer missing fields. Report exactly what's in the reference data.
"""

    return Agent(
        model=MODEL,
        name="order-lookup",
        description="Verifies order exists and extracts status, amount, delivery date.",
        instruction=get_instruction,
        output_key="order_lookup_output",
    )


# ---------------------------------------------------------------------------
# Stage 2: Refund Decision — Apply Rules
# ---------------------------------------------------------------------------

def _build_refund_decision_agent() -> Agent:
    """Refund decision agent — apply eligibility rules."""

    def get_instruction(ctx):
        order_data = ctx.state.get("order_lookup_output", "")
        return f"""{REFUND_POLICY}

---

{REFUND_DECISION_LOGIC}

---
## Order Data from Lookup

{order_data}

---
## Your Task

Apply the decision tree to this order and output the REFUND DECISION section.

Include:
- Decision: APPROVE | ESCALATE | REJECT
- Reason Code: [specific reason]
- Priority: HIGH | NORMAL | N/A
- Days Since Delivery: [from order data]
- Amount: [from order data]
"""

    return Agent(
        model=MODEL,
        name="refund-decision",
        description="Applies refund policy rules to order data.",
        instruction=get_instruction,
        output_key="refund_decision_output",
    )


# ---------------------------------------------------------------------------
# Stage 3: Fraud Detection — Screen for Abuse
# ---------------------------------------------------------------------------

def _build_fraud_detection_agent() -> Agent:
    """Fraud detection agent — screen for duplicate/frequency abuse."""

    def get_instruction(ctx):
        order_data = ctx.state.get("order_lookup_output", "")
        decision_data = ctx.state.get("refund_decision_output", "")
        fraud_flags = ctx.state.get("fraud_flags", "")
        return f"""{FRAUD_DETECTION_LOGIC}

---
## Order Data

{order_data}

## Current Decision

{decision_data}

## Fraud Signals Provided

{fraud_flags if fraud_flags else "(None reported)"}

---
## Your Task

Screen this refund for abuse patterns:

1. If decision is APPROVE (tentative):
   - Check if duplicate_refund_on_order (fraud signal present)
   - Check if customer_refund_count_30d > 3 (fraud signal present)
   - Override to ESCALATE if either check triggers

2. If decision is already ESCALATE or REJECT:
   - Fraud detection doesn't override
   - Pass through unchanged

Output format:

=== FRAUD SCREEN RESULT ===
Order ID:          [order_id]
Tentative Decision: [decision from above]
Duplicate Check:    PASS | FAIL (reason if fail)
Frequency Check:    PASS | FAIL (reason if fail)
Final Decision:     APPROVE (confirmed) | ESCALATE

NEXT STEP: customer-communication
"""

    return Agent(
        model=MODEL,
        name="fraud-detection",
        description="Screens tentatively-approved refunds for abuse patterns.",
        instruction=get_instruction,
        output_key="fraud_detection_output",
    )


# ---------------------------------------------------------------------------
# Stage 4: Customer Communication — Craft Response
# ---------------------------------------------------------------------------

def _build_communication_agent() -> Agent:
    """Customer communication agent — craft the customer-facing message."""

    def get_instruction(ctx):
        order_data = ctx.state.get("order_lookup_output", "")
        decision_data = ctx.state.get("refund_decision_output", "")
        fraud_data = ctx.state.get("fraud_detection_output", "")
        return f"""You are the final step of the refund pipeline — the customer-facing communicator.

Your job is to craft an appropriate response based on the decision.

## Reference Response Templates

{str(COMMUNICATION_TEMPLATES)}

---
## Full Pipeline Results

### Order Details
{order_data}

### Refund Decision
{decision_data}

### Fraud Check
{fraud_data}

---
## Your Task

1. Extract the final decision and reason code from fraud_data (or decision_data if no fraud check)
2. Choose the appropriate template from COMMUNICATION_TEMPLATES
3. Fill in placeholders: order_id, amount, days, ticket_id, etc.
4. Output the complete customer-facing message ready to send

Be warm, clear, and transparent. Never invent policy. Use the templates exactly.

---
## Output Format

=== CUSTOMER RESPONSE ===

[Full customer-facing message here, using the template]

---
DECISION SUMMARY:
- Final Decision: APPROVE | ESCALATE | REJECT
- Reason: [reason code]
- Ticket: [ticket_id if escalated, or N/A]
"""

    return Agent(
        model=MODEL,
        name="customer-communication",
        description="Crafts customer-facing messages for all outcomes.",
        instruction=get_instruction,
        output_key="customer_response",
    )


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------

def build_pipeline(run_name: str = "refund-demo-01") -> SequentialAgent:
    """Build the full refund processing pipeline."""
    return SequentialAgent(
        name="refund-pipeline",
        description="End-to-end customer refund processing pipeline.",
        agents=[
            _build_order_lookup_agent(),
            _build_refund_decision_agent(),
            _build_fraud_detection_agent(),
            _build_communication_agent(),
        ],
    )
