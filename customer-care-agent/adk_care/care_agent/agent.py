"""Customer Care Coordinator — Google ADK (M2: real handoff over A2A).

The conversational front desk. A single **LLM-routed** `Agent` that reads the
customer's message, classifies intent, does slot-filling, and — when a refund is
ready — **delegates to the refund specialist over the A2A protocol**.

The refund specialist runs as a separate **A2A server** (see
`refund-agent/adk_refund/a2a_server.py`, port 8043). Here it is consumed with the
official `RemoteA2aAgent`, pointed at the specialist's auto-generated Agent Card.
Docs: https://adk.dev/a2a/quickstart-consuming/

Policy/behavior lives **verbatim** in the bundled `SKILL.md`. The A2A wiring is
**host wiring** appended here — never written into the skill.

Run from `adk_care/`:  `adk web --port 8042 .`   (refund A2A server must be up.)
"""

from pathlib import Path

from google.adk.agents import Agent
from google.adk.agents.remote_a2a_agent import (
    AGENT_CARD_WELL_KNOWN_PATH,
    RemoteA2aAgent,
)

MODEL = "gemini-2.5-flash"

# Self-contained, bundled copy of the Claude-Code coordinator skill.
SKILLS_DIR = Path(__file__).parent / "skills" / "customer-care"


def load_skill(relpath: str) -> str:
    """Return the verbatim text of a bundled SKILL.md (no transformation)."""
    return (SKILLS_DIR / relpath).read_text(encoding="utf-8")


_coordinator_skill = load_skill("SKILL.md")

# --- The refund specialist, consumed over A2A (official RemoteA2aAgent) -----
REFUND_A2A_URL = f"http://localhost:8043{AGENT_CARD_WELL_KNOWN_PATH}"

refund_remote = RemoteA2aAgent(
    name="refund_agent",
    description=(
        "Remote refund specialist reached over A2A. Give it a customer order id "
        "and it returns the refund decision (APPROVE / ESCALATE / REJECT), reason "
        "code, and ticket if escalated."
    ),
    agent_card=REFUND_A2A_URL,
    use_legacy=False,
)

# --- Host wiring: the specialist is now really connected (NOT in the skill) --
_A2A_HOST_WIRING = """
---
## Host wiring — the refund specialist is connected (via A2A)

You are connected to a real refund specialist: a sub-agent named `refund_agent`
(a remote A2A service). When the customer wants a refund AND you have collected
their order id, delegate the task to `refund_agent`, passing the order id (e.g.
"Process refund for order <id>"). Let the specialist produce the decision, then
relay its outcome to the customer faithfully and warmly.

Never invent a refund decision, amount, or ticket yourself — that is the
specialist's job. If the order id is still missing, ask for it first (do not
delegate without it).
"""

# The only symbol ADK requires from this module.
root_agent = Agent(
    model=MODEL,
    name="care_agent",
    description=(
        "Conversational customer-care coordinator: greets the customer, "
        "understands intent across turns, fills required inputs, and delegates "
        "refunds to a remote specialist over A2A."
    ),
    instruction=_coordinator_skill + _A2A_HOST_WIRING,
    sub_agents=[refund_remote],
)
