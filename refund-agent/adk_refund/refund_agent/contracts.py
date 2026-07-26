"""Typed contracts for the local refund-control proof.

Amounts are integer cents to avoid floating-point currency errors.  These
models are deliberately framework-independent so the proof runs without ADK,
Firestore, or a payment provider.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RefundStatus(str, Enum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    ISSUED = "ISSUED"


@dataclass(frozen=True)
class RefundQuote:
    order_id: str
    amount_cents: int
    reason_code: str


@dataclass
class RefundRequest:
    request_id: str
    quote: RefundQuote
    idempotency_key: str
    status: RefundStatus = RefundStatus.PENDING_APPROVAL


@dataclass(frozen=True)
class Approval:
    request_id: str
    approver_id: str


@dataclass(frozen=True)
class IssuedRefund:
    refund_id: str
    request_id: str
    amount_cents: int


@dataclass(frozen=True)
class AuditEvent:
    event_type: str
    request_id: str
    actor_id: str
    trace_id: str
