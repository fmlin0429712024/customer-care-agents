#!/usr/bin/env python3
"""Simple Refund Pipeline using google-genai directly (no ADK complexity)."""

import os
import json
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from google import genai

load_dotenv()

API_KEY = os.getenv("GENAI_API_KEY")
MODEL = "gemini-2.5-flash"
DATA_DIR = Path(__file__).parent / "data"

if not API_KEY:
    print("ERROR: GENAI_API_KEY not set in .env")
    exit(1)

client = genai.Client(api_key=API_KEY)

# Reference data
ORDERS = {
    "12345": {"amount": 99, "status": "delivered", "delivery_date": "2026-07-02", "product": "Widget", "customer_id": "C001"},
    "67890": {"amount": 49, "status": "delivered", "delivery_date": "2026-07-07", "product": "Gadget", "customer_id": "C002"},
    "11111": {"amount": 29, "status": "in_transit", "delivery_date": None, "product": "Tool", "customer_id": "C003"},
}

REFUND_POLICY = """
## Refund Eligibility Rules

Within 5 days + amount ≤ $500 → AUTO-APPROVE
After 5 days → ESCALATE (reason: PAST_REFUND_WINDOW)
Amount > $500 → ESCALATE (reason: HIGH_VALUE_ORDER)
In transit → ESCALATE (reason: IN_TRANSIT)
Order not found → REJECT (reason: ORDER_NOT_FOUND)
"""

def lookup_order(order_id: str) -> dict:
    """Stage 1: Look up order."""
    if order_id not in ORDERS:
        return {"found": False, "status": "not_found"}

    order = ORDERS[order_id]
    return {
        "found": True,
        "order_id": order_id,
        "amount": order["amount"],
        "status": order["status"],
        "delivery_date": order["delivery_date"],
        "product": order["product"],
        "customer_id": order["customer_id"],
    }

async def decide_refund(order_id: str, order_data: dict) -> dict:
    """Stage 2: Decide refund eligibility using Gemini."""

    prompt = f"""{REFUND_POLICY}

---

Order Data:
{json.dumps(order_data, indent=2)}

Today's date: 2026-07-09

Decide if this refund should be AUTO_APPROVED, ESCALATED, or REJECTED.
Provide your decision in this format:

DECISION: [AUTO_APPROVED | ESCALATED | REJECTED]
REASON: [brief reason code]
EXPLANATION: [1-2 sentence explanation]
"""

    response = await asyncio.to_thread(
        client.models.generate_content,
        model=MODEL,
        contents=prompt,
    )

    text = response.text
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    result = {
        "order_id": order_id,
        "decision": "ESCALATED",
        "reason": "UNKNOWN",
        "explanation": text[:200],
    }

    for line in lines:
        if line.startswith("DECISION:"):
            result["decision"] = line.split(":", 1)[1].strip().split()[0]
        elif line.startswith("REASON:"):
            result["reason"] = line.split(":", 1)[1].strip()
        elif line.startswith("EXPLANATION:"):
            result["explanation"] = line.split(":", 1)[1].strip()

    return result

async def check_fraud(order_data: dict) -> dict:
    """Stage 3: Fraud check using Gemini."""

    prompt = f"""Check this order for fraud red flags:

Order Amount: ${order_data.get('amount', 0)}
Status: {order_data.get('status', 'unknown')}
Customer: {order_data.get('customer_id', 'unknown')}

Common fraud patterns:
- Multiple refunds in short time
- Amount > $1000
- Rush requests
- Mismatched customer info

Is this order suspicious? Answer YES or NO with brief explanation.
"""

    response = await asyncio.to_thread(
        client.models.generate_content,
        model=MODEL,
        contents=prompt,
    )

    text = response.text.upper()
    return {
        "flagged": "YES" in text,
        "details": response.text[:200],
    }

async def generate_response(order_id: str, decision: str, reason: str) -> str:
    """Stage 4: Generate customer message."""

    decision_normalized = decision.upper().replace("_", "")

    if "AUTO" in decision_normalized:
        template = f"""Dear Customer,

Your refund for order {order_id} has been approved and will be processed within 3-5 business days.

Thank you for your business!"""
    elif "REJECT" in decision_normalized:
        template = f"""Dear Customer,

Unfortunately, your refund request for order {order_id} cannot be processed at this time.

Reason: {reason}"""
    else:  # ESCALATED
        template = f"""Dear Customer,

Your refund request for order {order_id} requires further review due to: {reason}

A specialist will contact you within 24 hours.

Thank you for your patience!"""

    return template

async def run_refund(order_id: str):
    """Run the full refund pipeline."""
    print("\n" + "="*70)
    print(f"Processing refund request for order: {order_id}")
    print("="*70)

    # Stage 1: Lookup
    print(f"\n[1] Order Lookup...")
    order_data = lookup_order(order_id)
    if not order_data["found"]:
        print(f"   ❌ Order not found")
        return {
            "order_id": order_id,
            "decision": "REJECTED",
            "reason": "ORDER_NOT_FOUND",
        }
    print(f"   ✓ Order found: ${order_data['amount']} ({order_data['status']})")

    # Stage 2: Decision
    print(f"\n[2] Refund Decision...")
    decision = await decide_refund(order_id, order_data)
    print(f"   Decision: {decision['decision']}")
    print(f"   Reason: {decision['reason']}")

    # Stage 3: Fraud Check
    print(f"\n[3] Fraud Detection...")
    fraud = await check_fraud(order_data)
    if fraud["flagged"]:
        print(f"   ⚠️  Flagged: {fraud['details'][:100]}")
        decision["decision"] = "ESCALATED"
        decision["reason"] = "FRAUD_RISK"
    else:
        print(f"   ✓ No fraud detected")

    # Stage 4: Response
    print(f"\n[4] Customer Communication...")
    response = await generate_response(order_id, decision["decision"], decision["reason"])
    print(f"   Message:\n{response}")

    print("\n" + "="*70)
    print(f"Final Decision: {decision['decision']}")
    print("="*70 + "\n")

    return decision

# Test scenarios
SCENARIOS = {
    "scenario-1-auto-approve": "67890",
    "scenario-2-past-window": "12345",
    "scenario-3-in-transit": "11111",
}

async def main():
    import sys
    scenario = sys.argv[1] if len(sys.argv) > 1 else "scenario-1-auto-approve"
    order_id = SCENARIOS.get(scenario, "67890")
    await run_refund(order_id)

if __name__ == "__main__":
    asyncio.run(main())
