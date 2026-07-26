"""Deterministic control plane for a synthetic refund action.

The service, rather than an LLM, owns the PENDING_APPROVAL -> APPROVED ->
ISSUED state transition.  Its lock models the atomic transaction that a
production database would provide.
"""

from __future__ import annotations

from threading import Lock

from .audit import AuditLog
from .contracts import (
    Approval,
    AuditEvent,
    IssuedRefund,
    RefundQuote,
    RefundRequest,
    RefundStatus,
)


class RefundControlError(Exception):
    """A structured-control failure represented by a stable error code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class InMemoryRefundStore:
    """Synthetic source of truth used only by the runnable local proof."""

    def __init__(self) -> None:
        self.lock = Lock()
        self.requests: dict[str, RefundRequest] = {}
        self.request_by_key: dict[str, str] = {}
        self.approvals: dict[str, Approval] = {}
        self.issued: dict[str, IssuedRefund] = {}


class RefundService:
    """Implements deterministic quote, approval, issuance, and audit controls."""

    def __init__(self, store: InMemoryRefundStore, audit_log: AuditLog) -> None:
        self.store = store
        self.audit_log = audit_log
        self._request_sequence = 0
        self._refund_sequence = 0

    def calculate_quote(
        self, order_id: str, amount_cents: int, reason_code: str
    ) -> RefundQuote:
        if not order_id or amount_cents <= 0 or not reason_code:
            raise RefundControlError("INVALID_QUOTE_INPUT")
        return RefundQuote(order_id, amount_cents, reason_code)

    def create_refund_request(
        self, quote: RefundQuote, idempotency_key: str, actor_id: str, trace_id: str
    ) -> RefundRequest:
        if not idempotency_key:
            raise RefundControlError("MISSING_IDEMPOTENCY_KEY")
        with self.store.lock:
            existing_id = self.store.request_by_key.get(idempotency_key)
            if existing_id:
                return self.store.requests[existing_id]
            self._request_sequence += 1
            request = RefundRequest(
                request_id=f"REQ-{self._request_sequence}",
                quote=quote,
                idempotency_key=idempotency_key,
            )
            self.store.requests[request.request_id] = request
            self.store.request_by_key[idempotency_key] = request.request_id
            self._audit("REQUEST_CREATED", request.request_id, actor_id, trace_id)
            return request

    def approve_request(
        self, request_id: str, reviewer_id: str, trace_id: str
    ) -> Approval:
        # In production, reviewer identity comes from authenticated request context.
        if reviewer_id != "human_reviewer":
            raise RefundControlError("UNAUTHORIZED_REVIEWER")
        with self.store.lock:
            request = self._get_request(request_id)
            if request.status is not RefundStatus.PENDING_APPROVAL:
                raise RefundControlError("REQUEST_NOT_PENDING")
            approval = Approval(request_id=request_id, approver_id=reviewer_id)
            self.store.approvals[request_id] = approval
            request.status = RefundStatus.APPROVED
            self._audit("APPROVED", request_id, reviewer_id, trace_id)
            return approval

    def issue_refund(self, request_id: str, actor_id: str, trace_id: str) -> IssuedRefund:
        """Atomically issue once, or return the original issuance on a safe retry."""
        with self.store.lock:
            request = self._get_request(request_id)
            existing = self.store.issued.get(request_id)
            if existing:
                return existing
            if request.status is not RefundStatus.APPROVED:
                raise RefundControlError("APPROVAL_REQUIRED")
            if request_id not in self.store.approvals:
                raise RefundControlError("APPROVAL_RECORD_MISSING")
            self._refund_sequence += 1
            issued = IssuedRefund(
                refund_id=f"REF-{self._refund_sequence}",
                request_id=request_id,
                amount_cents=request.quote.amount_cents,
            )
            self.store.issued[request_id] = issued
            request.status = RefundStatus.ISSUED
            self._audit("REFUND_ISSUED", request_id, actor_id, trace_id)
            return issued

    def _get_request(self, request_id: str) -> RefundRequest:
        try:
            return self.store.requests[request_id]
        except KeyError as exc:
            raise RefundControlError("REQUEST_NOT_FOUND") from exc

    def _audit(self, event_type: str, request_id: str, actor_id: str, trace_id: str) -> None:
        self.audit_log.append(
            AuditEvent(
                event_type=event_type,
                request_id=request_id,
                actor_id=actor_id,
                trace_id=trace_id,
            )
        )
