"""Tools for the Refund Agent — data loading and reference data (self-contained)."""

import json
from pathlib import Path
from typing import Any

# Self-contained reference data — no external file dependencies
DATA_DIR = Path(__file__).parent.parent / "data"

# Orders reference (loaded from reference/)
ORDERS_REFERENCE = {
    "12345": {
        "order_id": "12345",
        "customer_id": "CUST001",
        "amount": 99.00,
        "status": "delivered",
        "order_date": "2026-07-02",
        "delivery_date": "2026-07-02",
        "product": "Widget Pro",
    },
    "67890": {
        "order_id": "67890",
        "customer_id": "CUST002",
        "amount": 49.00,
        "status": "delivered",
        "order_date": "2026-07-07",
        "delivery_date": "2026-07-07",
        "product": "Basic Widget",
    },
    "11111": {
        "order_id": "11111",
        "customer_id": "CUST003",
        "amount": 29.00,
        "status": "in_transit",
        "order_date": "2026-07-08",
        "delivery_date": None,
        "product": "Mini Widget",
    },
}


def list_scenarios() -> str:
    """List all available test scenarios."""
    scenarios = sorted([d.name for d in DATA_DIR.iterdir() if d.is_dir() and d.name.startswith("scenario-")])
    return "\n".join(scenarios)


def load_scenario_details(scenario_name: str) -> dict:
    """Load scenario details from JSON file."""
    details_file = DATA_DIR / scenario_name / "details.json"
    if details_file.exists():
        return json.loads(details_file.read_text())
    return {}


def get_orders_reference_json() -> str:
    """Return orders reference as JSON string."""
    return json.dumps({"orders": list(ORDERS_REFERENCE.values())}, indent=2)


def get_test_scenarios_reference() -> str:
    """Return test scenarios reference with expected outcomes."""
    scenarios = [
        {
            "scenario_id": "scenario-1-auto-approve",
            "order_id": "67890",
            "expected_decision": "APPROVE",
            "expected_reason": "AUTO_APPROVED",
        },
        {
            "scenario_id": "scenario-2-past-window",
            "order_id": "12345",
            "expected_decision": "ESCALATE",
            "expected_reason": "PAST_REFUND_WINDOW",
        },
        {
            "scenario_id": "scenario-3-in-transit",
            "order_id": "11111",
            "expected_decision": "ESCALATE",
            "expected_reason": "IN_TRANSIT",
        },
        {
            "scenario_id": "scenario-4-not-found",
            "order_id": "99999",
            "expected_decision": "REJECT",
            "expected_reason": "ORDER_NOT_FOUND",
        },
        {
            "scenario_id": "scenario-5-high-value",
            "order_id": "HIGH001",
            "expected_decision": "ESCALATE",
            "expected_reason": "HIGH_VALUE_ORDER",
        },
        {
            "scenario_id": "scenario-6-duplicate",
            "order_id": "67890",
            "expected_decision": "ESCALATE",
            "expected_reason": "DUPLICATE_REFUND",
        },
        {
            "scenario_id": "scenario-7-fraud-risk",
            "order_id": "67890",
            "expected_decision": "ESCALATE",
            "expected_reason": "FRAUD_RISK",
        },
    ]
    return json.dumps({"scenarios": scenarios}, indent=2)


def save_output(run_name: str, stage: str, output: str) -> str:
    """Save stage output to file."""
    output_dir = Path(__file__).parent.parent / "output" / run_name / stage
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"{stage}.txt"
    output_file.write_text(output)

    return f"Saved {stage} output to: {output_file}"
