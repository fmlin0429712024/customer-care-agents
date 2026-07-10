"""PII redaction guardrail — an ADK Plugin (cross-cutting governance layer).

Like the tracing wiring, this is NOT business logic: it imports no agent, no
tool, no SKILL.md. It is registered at the serve layer and applies to EVERY
LLM call across ALL sub-agents, redacting PII from the request *before* it
reaches the model — and therefore before it can leak into the traces.

Pattern: governance is injected at the wiring layer; agent.py / SKILL.md are
never touched. Same decoupling principle as observability.
"""

import re

from google.adk.plugins.base_plugin import BasePlugin

# Simple, explainable PII patterns (textbook demo — not exhaustive).
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
    """Redacts SSN / email / phone from every LLM request, for all agents."""

    def __init__(self, name: str = "pii_redaction") -> None:
        super().__init__(name=name)

    async def before_model_callback(self, *, callback_context, llm_request):
        redacted_count = 0
        # 1) Redact the conversation contents (where the customer's message lives)
        for content in llm_request.contents or []:
            for part in getattr(content, "parts", None) or []:
                if getattr(part, "text", None):
                    before = part.text
                    part.text = _redact(part.text)
                    if part.text != before:
                        redacted_count += 1
        print(f"[GUARDRAIL] before_model_callback fired — redacted {redacted_count} part(s)")

        # 2) Defensively redact the system instruction too, if it's plain text
        cfg = getattr(llm_request, "config", None)
        sys_inst = getattr(cfg, "system_instruction", None) if cfg else None
        if isinstance(sys_inst, str):
            cfg.system_instruction = _redact(sys_inst)

        # Return None → continue with the (now redacted) request.
        return None
