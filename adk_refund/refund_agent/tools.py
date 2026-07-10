"""Deterministic data-access tools for the refund pipeline (ADK FunctionTools).

These tools do I/O only — look up an order, read refund history, create a
ticket. They contain **no refund policy**: the 5-day window, $500 cap, and
escalation rules all live in the verbatim SKILL.md files. That split is the
point — SKILL.md holds business logic, tools.py holds data access.

Storage is **Cloud Firestore** (managed, serverless, persistent). Order
reference data is seeded on first use from the bundled
`skills/customer-refund/reference/orders.json`. Unlike the earlier SQLite
version, Firestore data survives container restarts and is shared across all
Cloud Run instances — so tickets persist and fraud history is globally correct.

The public tool signatures are unchanged from the SQLite version, so swapping
the storage layer touched only this file — never agent.py or any SKILL.md.
Collections are prefixed (`refund_*`) to stay isolated in a shared project.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from pathlib import Path

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

_PKG_DIR = Path(__file__).parent
_ORDERS_JSON = _PKG_DIR / "skills" / "customer-refund" / "reference" / "orders.json"

ORDERS_COLL = os.environ.get("REFUND_ORDERS_COLLECTION", "refund_orders")
TICKETS_COLL = os.environ.get("REFUND_TICKETS_COLLECTION", "refund_tickets")

# The reference "today" comes from the seed data so results are reproducible.
with _ORDERS_JSON.open(encoding="utf-8") as _f:
    _SEED = json.load(_f)
REFERENCE_TODAY = _SEED.get("notes", {}).get("reference_date", "2026-07-09")

_PRIORITY_SLA = {
    "HIGH": "1 hour response / 4 hour resolution",
    "NORMAL": "4 hour response / 24 hour resolution",
}

# One client per process; uses ADC locally, the service account on Cloud Run.
_db = firestore.Client(project=os.environ.get("GOOGLE_CLOUD_PROJECT"))


def _seed_orders() -> None:
    """Seed the orders collection from the bundled JSON if it is empty."""
    coll = _db.collection(ORDERS_COLL)
    if next(iter(coll.limit(1).stream()), None) is None:
        for o in _SEED.get("orders", []):
            coll.document(o["order_id"]).set(o)


_seed_orders()


def _days_since(delivery_date: str | None) -> int | None:
    if not delivery_date:
        return None
    d0 = datetime.strptime(delivery_date, "%Y-%m-%d").date()
    d1 = datetime.strptime(REFERENCE_TODAY, "%Y-%m-%d").date()
    return (d1 - d0).days


# ---------------------------------------------------------------------------
# Tools (passed to sub-agents via tools=[...])
# ---------------------------------------------------------------------------

def lookup_order(order_id: str) -> dict:
    """Look up a customer order by its ID and return its details.

    Reads the order record from the database and computes how many days have
    passed since delivery (relative to the reference date). Use this to verify
    an order exists before evaluating a refund.

    Args:
        order_id: The order ID the customer provided, e.g. "67890".

    Returns:
        A dict. If the order exists: found=True plus order_id, customer_id,
        amount, status, delivery_date, days_since_delivery (null if in transit),
        and product. If it does not exist: {"found": False, "order_id": ...}.
    """
    snap = _db.collection(ORDERS_COLL).document(order_id).get()
    if not snap.exists:
        return {"found": False, "order_id": order_id}
    o = snap.to_dict()
    return {
        "found": True,
        "order_id": o.get("order_id"),
        "customer_id": o.get("customer_id"),
        "amount": o.get("amount"),
        "status": o.get("status"),
        "delivery_date": o.get("delivery_date"),
        "days_since_delivery": _days_since(o.get("delivery_date")),
        "product": o.get("product"),
        "reference_today": REFERENCE_TODAY,
    }


def get_refund_history(customer_id: str) -> dict:
    """Return a customer's refund/escalation activity in the trailing 30 days.

    Used by fraud screening to detect frequency abuse. Counts escalation
    tickets opened for this customer within the last 30 days (relative to the
    reference date).

    Args:
        customer_id: The customer ID, e.g. "CUST002".

    Returns:
        A dict with customer_id and refund_count_30d (int).
    """
    ref = datetime.strptime(REFERENCE_TODAY, "%Y-%m-%d").date()
    docs = (
        _db.collection(TICKETS_COLL)
        .where(filter=FieldFilter("customer_id", "==", customer_id))
        .stream()
    )
    count = 0
    for d in docs:
        try:
            created = datetime.fromisoformat(d.to_dict().get("created_at")).date()
        except (TypeError, ValueError):
            continue
        if 0 <= (ref - created).days <= 30:
            count += 1
    return {"customer_id": customer_id, "refund_count_30d": count}


def create_escalation_ticket(order_id: str, customer_id: str, reason_code: str, priority: str) -> dict:
    """Create a human-review escalation ticket and return its ID and SLA.

    Generates a deterministic ticket ID, persists it, and returns the SLA for
    the given priority. Call this when the refund decision is ESCALATE.

    Args:
        order_id: The order being escalated, e.g. "12345".
        customer_id: The customer who owns the order, e.g. "CUST001".
        reason_code: The escalation reason, e.g. "PAST_REFUND_WINDOW".
        priority: "HIGH" or "NORMAL".

    Returns:
        A dict with ticket_id, order_id, reason_code, priority, sla, created_at.
    """
    priority = priority.upper()
    created_at = datetime.now().isoformat(timespec="seconds")
    ticket_id = f"ESCA-{datetime.now():%Y%m%d%H%M%S}-{uuid.uuid4().hex[:6].upper()}"
    record = {
        "ticket_id": ticket_id,
        "order_id": order_id,
        "customer_id": customer_id,
        "reason_code": reason_code,
        "priority": priority,
        "created_at": created_at,
    }
    _db.collection(TICKETS_COLL).document(ticket_id).set(record)
    return {**record, "sla": _PRIORITY_SLA.get(priority, _PRIORITY_SLA["NORMAL"])}
