"""Runnable proof for tool and approval boundaries; no cloud services required."""

from __future__ import annotations

import unittest

from refund_agent.audit import AuditLog
from refund_agent.refund_service import (
    InMemoryRefundStore,
    RefundControlError,
    RefundService,
)


class ToolBoundaryProofTest(unittest.TestCase):
    def setUp(self) -> None:
        self.audit = AuditLog()
        self.service = RefundService(InMemoryRefundStore(), self.audit)
        quote = self.service.calculate_quote("67890", 4900, "AUTO_APPROVED")
        self.request = self.service.create_refund_request(
            quote, "customer-67890-refund-1", "refund_agent", "trace-request"
        )

    def test_issuance_is_rejected_before_human_approval(self) -> None:
        with self.assertRaisesRegex(RefundControlError, "APPROVAL_REQUIRED"):
            self.service.issue_refund(
                self.request.request_id, "refund_service", "trace-before-approval"
            )
        self.assertEqual({}, self.service.store.issued)

    def test_authorized_reviewer_can_approve_then_issue(self) -> None:
        self.service.approve_request(
            self.request.request_id, "human_reviewer", "trace-approval"
        )
        issued = self.service.issue_refund(
            self.request.request_id, "refund_service", "trace-issued"
        )
        self.assertEqual(4900, issued.amount_cents)
        self.assertEqual(
            ["REQUEST_CREATED", "APPROVED", "REFUND_ISSUED"],
            [event.event_type for event in self.audit.events],
        )
        self.assertEqual("human_reviewer", self.audit.events[1].actor_id)

    def test_repeat_issuance_returns_original_refund(self) -> None:
        self.service.approve_request(
            self.request.request_id, "human_reviewer", "trace-approval"
        )
        first = self.service.issue_refund(
            self.request.request_id, "refund_service", "trace-first"
        )
        retry = self.service.issue_refund(
            self.request.request_id, "refund_service", "trace-retry"
        )
        self.assertEqual(first, retry)
        self.assertEqual(1, len(self.service.store.issued))
        self.assertEqual(1, sum(e.event_type == "REFUND_ISSUED" for e in self.audit.events))


if __name__ == "__main__":
    unittest.main()
