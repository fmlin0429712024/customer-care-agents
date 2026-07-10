"""Customer Refund Agent — Google ADK (textbook layout).

A `SequentialAgent` pipeline of four sub-agents. The split is deliberate:

  * Business logic (5-day window, $500 cap, escalation rules) lives in the
    verbatim `SKILL.md` files that Claude Code produced, bundled under
    `skills/customer-refund/` — byte-for-byte identical to
    `.claude/skills/customer-refund/`. To change policy, edit the SKILL.md.

  * Deterministic data access (order lookup, refund history, ticket creation)
    lives in `tools.py` as ADK FunctionTools backed by SQLite. The LLM calls
    these instead of guessing.

Run the playground from the parent folder (`adk_refund/`):

    adk web

then pick `refund_agent` and type e.g. "Process refund for order 67890".
"""

from pathlib import Path

from google.adk.agents import Agent, SequentialAgent

from .tools import lookup_order, get_refund_history, create_escalation_ticket

MODEL = "gemini-2.5-flash"

# Self-contained, bundled copy of the Claude-Code skill tree.
SKILLS_DIR = Path(__file__).parent / "skills" / "customer-refund"


def load_skill(relpath: str) -> str:
    """Return the verbatim text of a bundled SKILL.md (no transformation)."""
    return (SKILLS_DIR / relpath).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Stage 1: Order Lookup — verify & extract (tool: lookup_order)
# ---------------------------------------------------------------------------

def _build_order_lookup_agent() -> Agent:
    skill = load_skill("order-lookup/SKILL.md")
    instruction = f"""{skill}

---
## How to look up the order in this system

Call the `lookup_order` tool with the order ID the customer states in their
message. The tool returns the order record and the computed
`days_since_delivery` — do NOT compute dates yourself and do NOT invent data.
If the tool returns found=False, report ORDER_NOT_FOUND.

Then output the ORDER LOOKUP RESULT block exactly as the SKILL.md specifies.
"""
    return Agent(
        model=MODEL,
        name="order_lookup",
        description="Verifies order exists and extracts status, amount, delivery date.",
        instruction=instruction,
        tools=[lookup_order],
        output_key="order_lookup_output",
    )


# ---------------------------------------------------------------------------
# Stage 2: Refund Decision — apply rules (pure policy, no tools)
# ---------------------------------------------------------------------------

def _build_refund_decision_agent() -> Agent:
    policy_skill = load_skill("refund-policy/SKILL.md")
    decision_skill = load_skill("refund-decision/SKILL.md")

    def get_instruction(ctx):
        order_data = ctx.state.get("order_lookup_output", "")
        return f"""{policy_skill}

---

{decision_skill}

---
## Order Data from Lookup

{order_data}

---
## Your Task

Apply the decision tree from the SKILL.md above and output the REFUND DECISION:
- Decision: APPROVE | ESCALATE | REJECT
- Reason Code: [specific reason]
- Priority: HIGH | NORMAL | N/A
- Days Since Delivery: [from order data]
- Amount: [from order data]
"""

    return Agent(
        model=MODEL,
        name="refund_decision",
        description="Applies refund policy rules to order data.",
        instruction=get_instruction,
        output_key="refund_decision_output",
    )


# ---------------------------------------------------------------------------
# Stage 3: Fraud Detection — screen for abuse (tool: get_refund_history)
# ---------------------------------------------------------------------------

def _build_fraud_detection_agent() -> Agent:
    skill = load_skill("fraud-detection/SKILL.md")

    def get_instruction(ctx):
        order_data = ctx.state.get("order_lookup_output", "")
        decision_data = ctx.state.get("refund_decision_output", "")
        return f"""{skill}

---
## Order Data

{order_data}

## Current Decision

{decision_data}

---
## Your Task

Screen this refund using the SKILL.md logic above.
- If the decision is a tentative APPROVE: call `get_refund_history` with the
  customer_id from the order data. If refund_count_30d > 3, override to
  ESCALATE (FRAUD_RISK). Otherwise both checks PASS.
- If the decision is already ESCALATE or REJECT: pass it through unchanged
  (no tool call needed).

Output format:

=== FRAUD SCREEN RESULT ===
Order ID:           [order_id]
Tentative Decision: [decision from above]
Duplicate Check:    PASS | FAIL (reason if fail)
Frequency Check:    PASS | FAIL (reason if fail)
Final Decision:     APPROVE (confirmed) | ESCALATE

NEXT STEP: customer-communication
"""

    return Agent(
        model=MODEL,
        name="fraud_detection",
        description="Screens tentatively-approved refunds for abuse patterns.",
        instruction=get_instruction,
        tools=[get_refund_history],
        output_key="fraud_detection_output",
    )


# ---------------------------------------------------------------------------
# Stage 4: Customer Communication — craft response (tool: create_escalation_ticket)
# ---------------------------------------------------------------------------

def _build_communication_agent() -> Agent:
    skill = load_skill("customer-communication/SKILL.md")

    def get_instruction(ctx):
        order_data = ctx.state.get("order_lookup_output", "")
        decision_data = ctx.state.get("refund_decision_output", "")
        fraud_data = ctx.state.get("fraud_detection_output", "")
        return f"""{skill}

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

1. Determine the final decision and reason code from the fraud check (or the
   refund decision if no fraud check applied).
2. If the final decision is ESCALATE: call `create_escalation_ticket` with the
   order_id, customer_id, reason_code, and priority to obtain a REAL ticket ID
   and SLA. Use those exact values — never invent a ticket number.
3. Follow the SKILL.md tone-by-outcome and dialogue guidance to write the
   customer-facing message, filling in order_id, amount, days, ticket_id, etc.
4. End with a short DECISION SUMMARY:
   - Final Decision: APPROVE | ESCALATE | REJECT
   - Reason: [reason code]
   - Ticket: [ticket_id if escalated, or N/A]

Be warm, clear, and transparent. Never invent policy.
"""

    return Agent(
        model=MODEL,
        name="customer_communication",
        description="Crafts customer-facing messages for all outcomes.",
        instruction=get_instruction,
        tools=[create_escalation_ticket],
        output_key="customer_response",
    )


# ---------------------------------------------------------------------------
# Root agent — the only element ADK requires in this module.
# ---------------------------------------------------------------------------

root_agent = SequentialAgent(
    name="refund_pipeline",
    description="End-to-end customer refund processing pipeline.",
    sub_agents=[
        _build_order_lookup_agent(),
        _build_refund_decision_agent(),
        _build_fraud_detection_agent(),
        _build_communication_agent(),
    ],
)
