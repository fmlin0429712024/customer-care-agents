#!/usr/bin/env python3
"""Streamlit UI for the Refund Agent."""

import os
import json
import asyncio
import streamlit as st
from dotenv import load_dotenv
from google import genai

load_dotenv()

API_KEY = os.getenv("GENAI_API_KEY")
MODEL = "gemini-2.5-flash"

if not API_KEY:
    st.error("❌ GENAI_API_KEY not set in .env")
    st.stop()

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

def generate_response(order_id: str, decision: str, reason: str) -> str:
    """Stage 4: Generate customer message."""

    decision_normalized = decision.upper().replace("_", "")

    if "AUTO" in decision_normalized:
        return f"""Dear Customer,

Your refund for order {order_id} has been approved and will be processed within 3-5 business days.

Thank you for your business!"""
    elif "REJECT" in decision_normalized:
        return f"""Dear Customer,

Unfortunately, your refund request for order {order_id} cannot be processed at this time.

Reason: {reason}

Please contact support if you have questions."""
    else:  # ESCALATED
        return f"""Dear Customer,

Your refund request for order {order_id} requires further review due to: {reason}

A specialist will contact you within 24 hours.

Thank you for your patience!"""

async def process_refund(order_id: str):
    """Run the full refund pipeline."""

    # Stage 1: Lookup
    st.info("📋 **Stage 1: Order Lookup**")
    order_data = lookup_order(order_id)
    if not order_data["found"]:
        st.error(f"❌ Order {order_id} not found")
        return None

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Order ID", order_id)
    with col2:
        st.metric("Amount", f"${order_data['amount']}")
    with col3:
        st.metric("Status", order_data['status'])
    with col4:
        st.metric("Days", "7" if order_data['status'] == 'delivered' else "—")

    st.success(f"✓ Order found")

    # Stage 2: Decision
    st.info("🤔 **Stage 2: Refund Decision** (using Gemini)")
    with st.spinner("Applying refund policy rules..."):
        decision = await decide_refund(order_id, order_data)

    # Stage 3: Fraud Check
    st.info("🔍 **Stage 3: Fraud Detection** (using Gemini)")
    with st.spinner("Checking for fraud red flags..."):
        fraud = await check_fraud(order_data)

    if fraud["flagged"]:
        st.warning(f"⚠️ Fraud detected: {fraud['details'][:100]}")
        decision["decision"] = "ESCALATED"
        decision["reason"] = "FRAUD_RISK"
    else:
        st.success("✓ No fraud detected")

    # Stage 4: Response
    st.info("📧 **Stage 4: Customer Communication**")
    message = generate_response(order_id, decision["decision"], decision["reason"])

    # Display decision
    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        if "AUTO" in decision["decision"].upper():
            st.success(f"✅ **DECISION: {decision['decision']}**")
        elif "REJECT" in decision["decision"].upper():
            st.error(f"❌ **DECISION: {decision['decision']}**")
        else:
            st.warning(f"⏳ **DECISION: {decision['decision']}**")

    with col2:
        st.caption(f"**Reason:** {decision['reason']}")

    st.text_area("📝 Explanation", decision['explanation'], disabled=True, height=80)
    st.text_area("📧 Customer Message", message, disabled=True, height=120)

    return decision

# Streamlit UI
st.set_page_config(
    page_title="Refund Agent",
    page_icon="🎁",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🎁 Customer Refund Agent")
st.markdown("Process customer refunds with AI-powered decision making")

# Sidebar
with st.sidebar:
    st.header("About")
    st.write("""
    This app processes customer refund requests through a 4-stage pipeline:

    1. **Order Lookup** - Verify order exists
    2. **Refund Decision** - Apply policy rules (using Gemini)
    3. **Fraud Detection** - Screen for abuse (using Gemini)
    4. **Customer Communication** - Generate message
    """)

    st.divider()
    st.subheader("Test Orders")
    st.write("**Order 67890:** $49, delivered 2 days ago → ✅ Auto-Approve")
    st.write("**Order 12345:** $99, delivered 7 days ago → ⏳ Escalate")
    st.write("**Order 11111:** $29, in transit → ⏳ Escalate")

# Main content
col1, col2 = st.columns([2, 1])

with col1:
    order_id = st.text_input(
        "Enter Order ID to Process",
        placeholder="e.g., 67890",
        help="Enter a customer's order ID to process their refund request"
    )

with col2:
    st.write("")  # Add spacing
    st.write("")
    if st.button("🚀 Process Refund", use_container_width=True):
        if not order_id:
            st.error("Please enter an Order ID")
        else:
            asyncio.run(process_refund(order_id.strip()))

# Quick test buttons
st.divider()
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("📊 Test: Auto-Approve (67890)", use_container_width=True):
        asyncio.run(process_refund("67890"))

with col2:
    if st.button("📊 Test: Escalate Past Window (12345)", use_container_width=True):
        asyncio.run(process_refund("12345"))

with col3:
    if st.button("📊 Test: Escalate In-Transit (11111)", use_container_width=True):
        asyncio.run(process_refund("11111"))

st.divider()
st.caption("Powered by Google Gemini 2.5 Flash | Running on localhost")
