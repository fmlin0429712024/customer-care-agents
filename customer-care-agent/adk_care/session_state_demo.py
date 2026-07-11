"""Session & State — the worked example (localhost, InMemorySessionService).

Isolates the middle two of the four terms, and contrasts them with memory:

    STATE   = a STRUCTURED sticky-note inside ONE session.
              Survives across TURNS. Dies when the session ends.  (does NOT cross boxes)
    MEMORY  = survives ACROSS sessions.                            (crosses boxes — see m3_memory_demo.py)

Use case: slot-filling. The agent needs an order_id to act. Across turns in the
SAME session it collects order_id INTO state (set_order_id), and can read it back
(get_order_id) without asking twice. A brand-new session starts with EMPTY state.

The proof is the printed `session.state` after each turn: {} -> {order_id: ...}
-> persists, then {} again in a new box.

State vs history: within a session, the raw transcript also carries the order, but
STATE is the deliberate, structured key-value a tool writes — readable
deterministically and surviving even if history is later compacted (M4).

App level: InMemorySessionService (single process). On Cloud Run (stateless,
multi-instance) this would be swapped for DatabaseSessionService — same code, the
state just externalizes to a DB. "Swap the backend, not the concept."

Run from adk_care/ :   .venv/bin/python session_state_demo.py
"""

import asyncio
from pathlib import Path

from dotenv import load_dotenv

# Vertex model auth before building the agent.
load_dotenv(Path(__file__).parent / "care_agent" / ".env")

from google.adk.agents import Agent  # noqa: E402
from google.adk.runners import Runner  # noqa: E402
from google.adk.sessions import InMemorySessionService  # noqa: E402
from google.adk.tools.tool_context import ToolContext  # noqa: E402
from google.genai import types  # noqa: E402

APP = "care_state_demo"
USER = "amy"
MODEL = "gemini-2.5-flash"

SKILL = (
    Path(__file__).parent / "care_agent" / "skills" / "customer-care" / "SKILL.md"
).read_text(encoding="utf-8")


# --- Tools that WRITE and READ the session's structured sticky-note (state) ---
def set_order_id(order_id: str, tool_context: ToolContext) -> dict:
    """Save the customer's order id into this session's state (slot-filling)."""
    tool_context.state["order_id"] = order_id
    return {"status": "saved", "order_id": order_id}


def get_order_id(tool_context: ToolContext) -> dict:
    """Read the order id already collected in this session, if any."""
    oid = tool_context.state.get("order_id")
    if oid:
        return {"order_id": oid}
    return {"order_id": None, "note": "no order id on file for this session yet"}


_STATE_WIRING = """
---
## Host wiring — session state (slot-filling)

You have two tools for the order id:
- When the customer gives an order number, CALL `set_order_id` to record it.
- When you need or are asked for the order number already provided, CALL
  `get_order_id` to read it back — do NOT ask the customer to repeat it if it is
  already on file for this session.
Keep replies short.
"""

agent = Agent(
    model=MODEL,
    name="care_agent",
    instruction=SKILL + _STATE_WIRING,
    tools=[set_order_id, get_order_id],
)

session_service = InMemorySessionService()
runner = Runner(agent=agent, app_name=APP, session_service=session_service)


async def say(session_id: str, text: str) -> None:
    """One user turn; show tool calls + reply, then print the state sticky-note."""
    print(f"\n  👤 Amy: {text}")
    msg = types.Content(role="user", parts=[types.Part(text=text)])
    final = ""
    async for ev in runner.run_async(user_id=USER, session_id=session_id, new_message=msg):
        for part in (ev.content.parts if ev.content else None) or []:
            if getattr(part, "function_call", None):
                fc = part.function_call
                print(f"     ⚙️  tool call: {fc.name}({dict(fc.args)})")
        if ev.is_final_response() and ev.content:
            final = "".join(p.text for p in ev.content.parts if getattr(p, "text", None))
    if final:
        print(f"  🤖 care: {final.strip()}")
    sess = await session_service.get_session(app_name=APP, user_id=USER, session_id=session_id)
    print(f"     📝 session.state = {dict(sess.state)}")


async def main() -> None:
    print("=" * 72)
    print("SESSION A  —  one conversation (box #1). Watch state fill across TURNS.")
    print("=" * 72)
    a = await session_service.create_session(app_name=APP, user_id=USER)
    await say(a.id, "Hi, I'd like a refund.")                 # state empty
    await say(a.id, "My order number is 12345.")              # -> state {order_id: 12345}
    await say(a.id, "Sorry, what order number did I give you?")  # reads state, no re-ask

    print("\n" + "=" * 72)
    print("SESSION B  —  a BRAND-NEW conversation (box #2). State starts EMPTY.")
    print("=" * 72)
    b = await session_service.create_session(app_name=APP, user_id=USER)
    await say(b.id, "What's my order number?")                # empty -> cannot know

    print("\n" + "=" * 72)
    print("STATE crossed TURNS inside box #1, but did NOT cross into box #2.")
    print("Contrast memory (m3_memory_demo.py), which DOES cross boxes.")
    print("=" * 72)


if __name__ == "__main__":
    asyncio.run(main())
