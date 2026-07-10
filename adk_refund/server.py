#!/usr/bin/env python3
"""FastAPI server for the Refund Agent with web interface."""

import os
import json
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from google import genai

load_dotenv()

API_KEY = os.getenv("GENAI_API_KEY")
MODEL = "gemini-2.5-flash"

if not API_KEY:
    print("ERROR: GENAI_API_KEY not set")
    exit(1)

client = genai.Client(api_key=API_KEY)
app = FastAPI(title="Customer Refund Agent", version="1.0.0")

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

class RefundRequest(BaseModel):
    order_id: str

class RefundResponse(BaseModel):
    order_id: str
    decision: str
    reason: str
    explanation: str
    message: str

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

# API Endpoints

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the web UI."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Customer Refund Agent</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }
            .container {
                background: white;
                border-radius: 12px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                width: 100%;
                max-width: 600px;
                padding: 40px;
            }
            h1 {
                color: #333;
                margin-bottom: 30px;
                text-align: center;
                font-size: 28px;
            }
            .form-group {
                margin-bottom: 20px;
            }
            label {
                display: block;
                margin-bottom: 8px;
                color: #555;
                font-weight: 600;
            }
            input {
                width: 100%;
                padding: 12px;
                border: 2px solid #ddd;
                border-radius: 6px;
                font-size: 16px;
                transition: border-color 0.3s;
            }
            input:focus {
                outline: none;
                border-color: #667eea;
            }
            button {
                width: 100%;
                padding: 12px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s;
            }
            button:hover {
                transform: translateY(-2px);
            }
            button:active {
                transform: translateY(0);
            }
            .result {
                margin-top: 30px;
                padding: 20px;
                background: #f8f9fa;
                border-radius: 8px;
                display: none;
            }
            .result.show {
                display: block;
            }
            .decision {
                font-size: 18px;
                font-weight: 700;
                margin-bottom: 12px;
                padding: 12px;
                border-radius: 6px;
                text-align: center;
            }
            .decision.approved {
                background: #d4edda;
                color: #155724;
            }
            .decision.escalated {
                background: #fff3cd;
                color: #856404;
            }
            .decision.rejected {
                background: #f8d7da;
                color: #721c24;
            }
            .message {
                background: white;
                padding: 15px;
                border-left: 4px solid #667eea;
                margin-top: 15px;
                white-space: pre-wrap;
                line-height: 1.6;
                color: #333;
            }
            .loading {
                text-align: center;
                color: #667eea;
                display: none;
            }
            .error {
                background: #f8d7da;
                color: #721c24;
                padding: 15px;
                border-radius: 6px;
                margin-top: 15px;
                display: none;
            }
            .test-buttons {
                display: grid;
                grid-template-columns: 1fr 1fr 1fr;
                gap: 10px;
                margin-bottom: 20px;
            }
            .test-btn {
                padding: 10px;
                background: #e9ecef;
                color: #333;
                border: 1px solid #ddd;
                border-radius: 6px;
                cursor: pointer;
                font-size: 13px;
                font-weight: 600;
                transition: all 0.2s;
            }
            .test-btn:hover {
                background: #dee2e6;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎁 Customer Refund Agent</h1>

            <div class="test-buttons">
                <button class="test-btn" onclick="setOrder('67890')">Test Auto-Approve</button>
                <button class="test-btn" onclick="setOrder('12345')">Test Escalate</button>
                <button class="test-btn" onclick="setOrder('11111')">Test In-Transit</button>
            </div>

            <form onsubmit="processRefund(event)">
                <div class="form-group">
                    <label for="order_id">Order ID:</label>
                    <input type="text" id="order_id" name="order_id" placeholder="e.g., 67890" required>
                </div>
                <button type="submit">Process Refund</button>
            </form>

            <div class="loading" id="loading">⏳ Processing refund request...</div>
            <div class="error" id="error"></div>
            <div class="result" id="result">
                <div class="decision" id="decision"></div>
                <div><strong>Reason:</strong> <span id="reason"></span></div>
                <div><strong>Explanation:</strong> <span id="explanation"></span></div>
                <div class="message" id="message"></div>
            </div>
        </div>

        <script>
            function setOrder(orderId) {
                document.getElementById('order_id').value = orderId;
                processRefund({ preventDefault: () => {} });
            }

            async function processRefund(e) {
                e.preventDefault();
                const orderId = document.getElementById('order_id').value;

                document.getElementById('loading').style.display = 'block';
                document.getElementById('result').classList.remove('show');
                document.getElementById('error').style.display = 'none';

                try {
                    const response = await fetch('/api/refund', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ order_id: orderId }),
                    });

                    if (!response.ok) {
                        const errorData = await response.json();
                        throw new Error(errorData.detail || 'Request failed');
                    }

                    const data = await response.json();

                    document.getElementById('loading').style.display = 'none';
                    document.getElementById('decision').textContent = `Decision: ${data.decision}`;
                    document.getElementById('decision').className = 'decision ' + data.decision.toLowerCase().replace('_', '');
                    document.getElementById('reason').textContent = data.reason;
                    document.getElementById('explanation').textContent = data.explanation;
                    document.getElementById('message').textContent = data.message;
                    document.getElementById('result').classList.add('show');
                } catch (error) {
                    document.getElementById('loading').style.display = 'none';
                    document.getElementById('error').textContent = '❌ Error: ' + error.message;
                    document.getElementById('error').style.display = 'block';
                }
            }
        </script>
    </body>
    </html>
    """

@app.post("/api/refund", response_model=RefundResponse)
async def process_refund(request: RefundRequest):
    """Process a refund request through all 4 stages."""

    order_id = request.order_id.strip()

    # Stage 1: Lookup
    order_data = lookup_order(order_id)
    if not order_data["found"]:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

    # Stage 2: Decision
    decision = await decide_refund(order_id, order_data)

    # Stage 3: Fraud Check
    fraud = await check_fraud(order_data)
    if fraud["flagged"]:
        decision["decision"] = "ESCALATED"
        decision["reason"] = "FRAUD_RISK"

    # Stage 4: Response
    message = generate_response(order_id, decision["decision"], decision["reason"])

    return RefundResponse(
        order_id=order_id,
        decision=decision["decision"],
        reason=decision["reason"],
        explanation=decision["explanation"],
        message=message,
    )

@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "model": MODEL}

@app.get("/api/orders")
async def list_orders():
    """List all available test orders."""
    return {
        "orders": [
            {"id": "67890", "amount": 49, "status": "delivered", "scenario": "auto-approve"},
            {"id": "12345", "amount": 99, "status": "delivered", "scenario": "escalate-past-window"},
            {"id": "11111", "amount": 29, "status": "in_transit", "scenario": "escalate-in-transit"},
        ]
    }

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*70)
    print("🚀 Starting Refund Agent Server")
    print("="*70)
    print("\n📍 Open your browser to: http://localhost:8000")
    print("\n✨ Features:")
    print("   • Web UI at http://localhost:8000")
    print("   • API at http://localhost:8000/api/refund (POST)")
    print("   • Test orders: 67890, 12345, 11111")
    print("\n" + "="*70 + "\n")
    uvicorn.run(app, host="127.0.0.1", port=8000)
