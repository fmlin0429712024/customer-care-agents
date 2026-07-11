"""M3 — cross-session memory (localhost, InMemoryMemoryService).

Demonstrates the one thing that separates a coordinator from a one-shot worker:
it remembers a returning customer ACROSS sessions.

Two sessions, SAME user_id, ONE running process:

    Session 1 (Amy, first visit)         -> conversation saved into memory
       |  add_session_to_memory(...)        (the cross-box bridge)
       v
    Session 2 (Amy returns, NEW session) -> agent recalls via the load_memory tool

Backend is InMemoryMemoryService: recall works across sessions WITHIN this
process (not across restarts — it lives in RAM). Swap it for
VertexAiMemoryBankService later to persist; the agent code barely changes.
"Cloud swaps the backend, not the concept."

Policy (SKILL.md) is reused verbatim; memory is HOST WIRING added here, never in
the skill. The A2A refund sub-agent is intentionally omitted — this demo is about
memory, so it needs no refund server and no Firestore.

Run from adk_care/ :   .venv/bin/python m3_memory_demo.py
"""

import asyncio
from pathlib import Path

from dotenv import load_dotenv

# Vertex model auth must be set BEFORE the agent/model is built.
load_dotenv(Path(__file__).parent / "care_agent" / ".env")

from google.adk.agents import Agent  # noqa: E402
from google.adk.memory import InMemoryMemoryService  # noqa: E402
from google.adk.runners import Runner  # noqa: E402
from google.adk.sessions import InMemorySessionService  # noqa: E402
from google.adk.tools import load_memory  # noqa: E402
from google.genai import types  # noqa: E402

APP = "care_memory_demo"
USER = "amy"  # the SAME customer identity across both sessions
MODEL = "gemini-2.5-flash"

# Reuse the coordinator policy verbatim (same file the playground agent loads).
SKILL = (
    Path(__file__).parent / "care_agent" / "skills" / "customer-care" / "SKILL.md"
).read_text(encoding="utf-8")

# Host wiring for long-term memory — appended here, NOT written into SKILL.md.
_MEMORY_WIRING = """
---
## Host wiring — long-term memory (M3)

You can remember returning customers across visits. When the customer refers to a
past interaction ("last time", "my previous refund", "do you remember me?"), CALL
the `load_memory` tool with a short query to recall it, then answer warmly using
what you recall (name the order and ticket if you have them). Never invent facts
you could not recall.
"""

agent = Agent(
    model=MODEL,
    name="care_agent",
    instruction=SKILL + _MEMORY_WIRING,
    tools=[load_memory],
)

session_service = InMemorySessionService()
memory_service = InMemoryMemoryService()
runner = Runner(
    agent=agent,
    app_name=APP,
    session_service=session_service,
    memory_service=memory_service,
)


async def say(session_id: str, text: str) -> str:
    """Send one user turn; print any memory tool call + the final reply."""
    print(f"\n  👤 Amy: {text}")
    msg = types.Content(role="user", parts=[types.Part(text=text)])
    final = ""
    async for ev in runner.run_async(
        user_id=USER, session_id=session_id, new_message=msg
    ):
        for part in (ev.content.parts if ev.content else None) or []:
            if getattr(part, "function_call", None):  # make retrieval VISIBLE
                fc = part.function_call
                print(f"     ⚙️  tool call: {fc.name}(query={dict(fc.args)})")
        if ev.is_final_response() and ev.content:
            final = "".join(p.text for p in ev.content.parts if getattr(p, "text", None))
    if final:
        print(f"  🤖 care: {final.strip()}")
    return final


async def main() -> None:
    print("=" * 72)
    print("SESSION 1  —  Amy's first visit   (box #1)")
    print("=" * 72)
    s1 = await session_service.create_session(app_name=APP, user_id=USER)
    await say(
        s1.id,
        "Hi, I'm Amy. Last week I asked for a refund on order 12345. It was "
        "escalated and the ticket number I was given was ESCA-88.",
    )
    await say(s1.id, "Okay, thank you — I'll check back later.")

    # --- The cross-box bridge: persist session 1 into long-term memory ---
    completed = await session_service.get_session(
        app_name=APP, user_id=USER, session_id=s1.id
    )
    await memory_service.add_session_to_memory(completed)
    print("\n  💾 [memory] session 1 saved to InMemoryMemoryService")

    print("\n" + "=" * 72)
    print("SESSION 2  —  Amy returns, a BRAND-NEW session   (box #2, empty state)")
    print("=" * 72)
    s2 = await session_service.create_session(app_name=APP, user_id=USER)
    await say(
        s2.id,
        "Hi, it's Amy again. Do you remember what happened with my refund last time?",
    )

    print("\n" + "=" * 72)
    print("Box #2 started empty. If care named order 12345 / ticket ESCA-88 above,")
    print("that came from MEMORY (add_session_to_memory -> load_memory), not state.")
    print("=" * 72)


if __name__ == "__main__":
    asyncio.run(main())
