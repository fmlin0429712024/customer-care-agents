"""Append-only audit helper for the local refund-control proof."""

from __future__ import annotations

from .contracts import AuditEvent


class AuditLog:
    """Small in-memory event log; production can replace this with durable storage."""

    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def append(self, event: AuditEvent) -> None:
        self.events.append(event)
