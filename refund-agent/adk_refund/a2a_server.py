"""Expose the refund worker as an A2A server — official ADK `to_a2a`.

The worker's own code (refund_agent/agent.py) is untouched. This file wraps its
existing `root_agent` for A2A, and is **Cloud-Run-ready**: it binds 0.0.0.0:$PORT
and advertises the correct public Agent Card URL.

Local:
    uvicorn a2a_server:a2a_app --host localhost --port 8043
    # card at http://localhost:8043/.well-known/agent-card.json

Cloud Run (the card MUST advertise the public URL, not localhost):
    A2A_PUBLIC_URL=https://refund-agent-....run.app  python a2a_server.py
"""

import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

# Load the worker's env (Vertex + Firestore) BEFORE importing the agent —
# tools.py creates a Firestore client at import time, so the project must be set.
load_dotenv(Path(__file__).parent / "refund_agent" / ".env")

from google.adk.a2a.utils.agent_to_a2a import to_a2a  # noqa: E402
from refund_agent.agent import root_agent  # noqa: E402

# The port uvicorn binds (Cloud Run injects $PORT).
PORT = int(os.environ.get("PORT", "8043"))

# The Agent Card advertises an rpc_url built from host/port/protocol. On Cloud
# Run the reachable URL is the public https *.run.app host (not localhost:$PORT),
# so derive the card's host/port/protocol from A2A_PUBLIC_URL when set.
_public = os.environ.get("A2A_PUBLIC_URL")
if _public:
    u = urlparse(_public)
    _proto = u.scheme or "https"
    a2a_app = to_a2a(
        root_agent,
        host=u.hostname,
        port=u.port or (443 if _proto == "https" else 80),
        protocol=_proto,
    )
else:
    a2a_app = to_a2a(root_agent, port=PORT)  # local: card advertises localhost:$PORT


if __name__ == "__main__":
    import uvicorn

    # 0.0.0.0 so a container accepts external traffic on Cloud Run.
    uvicorn.run(a2a_app, host="0.0.0.0", port=PORT)
