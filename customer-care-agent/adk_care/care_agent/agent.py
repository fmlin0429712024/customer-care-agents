"""Customer Care Coordinator — Google ADK (M0: solo, stub handoff).

The conversational front desk. Unlike the refund worker (a fixed
`SequentialAgent`), this is a single **LLM-routed** `Agent`: it reads the
customer's message, classifies intent, does slot-filling, and *would* hand off
to a specialist.

At M0 it runs **SOLO** — no worker is connected — so the handoff is a **stub**:
it emits what it *would* dispatch instead of calling anything. This isolates the
coordinator so we can verify routing + slot-filling before wiring the worker
(M2), memory (M3), or context management (M4).

Policy/behavior lives **verbatim** in the bundled `SKILL.md` (byte-identical to
`.claude/skills/customer-care/`). The M0 stub is **host wiring** appended here —
never written into the skill. Same split the worker uses.

Run from `adk_care/`:  `adk web`  → pick `care_agent`.
"""

from pathlib import Path

from google.adk.agents import Agent

MODEL = "gemini-2.5-flash"

# Self-contained, bundled copy of the Claude-Code coordinator skill.
SKILLS_DIR = Path(__file__).parent / "skills" / "customer-care"


def load_skill(relpath: str) -> str:
    """Return the verbatim text of a bundled SKILL.md (no transformation)."""
    return (SKILLS_DIR / relpath).read_text(encoding="utf-8")


_coordinator_skill = load_skill("SKILL.md")

# --- Host wiring: M0 stub handoff (NOT part of the skill) -------------------
_M0_HOST_WIRING = """
---
## M0 host wiring — solo run (no specialist connected)

You are running STANDALONE for milestone M0. No refund worker is wired in yet,
so you CANNOT actually hand off and you must NOT invent a refund decision,
amount, or ticket. Follow the SKILL.md exactly for greeting, intent routing,
and slot-filling. At the moment you WOULD hand off to the refund specialist,
emit a single stub line:

    [STUB HANDOFF -> refund]  { intent: "refund", order_id: "<the id>" }

then tell the customer the request has been captured and would be routed to the
refund specialist (not online in this milestone). This lets us verify routing
and slot-filling before any specialist, memory, or context management is added.
"""

# The only symbol ADK requires from this module.
root_agent = Agent(
    model=MODEL,
    name="care_agent",
    description=(
        "Conversational customer-care coordinator: greets the customer, "
        "understands intent across turns, fills required inputs, and routes to "
        "a specialist (refund handoff is stubbed at M0)."
    ),
    instruction=_coordinator_skill + _M0_HOST_WIRING,
)
