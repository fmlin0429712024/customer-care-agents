"""PII redaction guardrail for the care coordinator — an ADK Plugin.

Care is the **first line of defense**: the customer's raw PII enters the system
here (the intake), before anything is delegated to the refund worker over A2A.
So the coordinator redacts SSN / email / phone from every LLM request, before the
model call — and therefore before it can leak into traces or across the A2A hop.

Governance is injected at the serve layer (`serve.py` via `extra_plugins`);
agent.py / SKILL.md are never touched. Same decoupling as the worker's guardrail.
"""

import re

from google.adk.plugins.base_plugin import BasePlugin

_PATTERNS = [
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED_SSN]"),
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "[REDACTED_EMAIL]"),
    (re.compile(r"\b\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"), "[REDACTED_PHONE]"),
]


def _redact(text: str) -> str:
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text


class PIIRedactionPlugin(BasePlugin):
    """Redacts SSN / email / phone from every LLM request in the coordinator."""

    def __init__(self, name: str = "pii_redaction") -> None:
        super().__init__(name=name)

    async def before_model_callback(self, *, callback_context, llm_request):
        redacted = 0
        for content in llm_request.contents or []:
            for part in getattr(content, "parts", None) or []:
                if getattr(part, "text", None):
                    before = part.text
                    part.text = _redact(part.text)
                    if part.text != before:
                        redacted += 1
        print(f"[GUARDRAIL] care before_model_callback fired — redacted {redacted} part(s)")
        return None
