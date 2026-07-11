"""Cloud-Run-ready serve entry for the care coordinator — full app-level harness.

ONE entrypoint that wires the whole harness around the agent, the same way a
Cloud Run container runs it:

  - Governance : PII guardrail (redacts before every model call) via extra_plugins
  - Observability : tracing to Cloud Trace (TRACE_TO_CLOUD=on)
  - Harness : session + memory services (InMemory locally; point *_SERVICE_URI at
    a durable store on Cloud Run — "swap the backend, not the concept")
  - The ADK playground (web=True) for interactive testing

Binds 0.0.0.0:$PORT, so the identical file runs locally and on Cloud Run. The
refund worker's A2A server must be reachable at REFUND_A2A_BASE_URL
(default http://localhost:8043 for local).

Run locally:  .venv/bin/python serve.py        # PORT defaults to 8042
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Vertex model auth (+ any local config) before the app/agent is built.
load_dotenv(Path(__file__).parent / "care_agent" / ".env")

import uvicorn  # noqa: E402
from google.adk.cli.fast_api import get_fast_api_app  # noqa: E402

AGENTS_DIR = str(Path(__file__).parent)
PORT = int(os.environ.get("PORT", "8042"))

# Governance: PII guardrail as a plugin — care is the FIRST line (PII enters here).
extra_plugins = None
if os.environ.get("PII_GUARDRAIL", "on").lower() != "off":
    extra_plugins = ["guardrails.PIIRedactionPlugin"]
    print("[guardrail] care PII redaction ENABLED")
else:
    print("[guardrail] care PII redaction OFF")

# Harness backends: InMemory by default (local); set these to a durable store
# (DB / Memory Bank) on Cloud Run, since Cloud Run is stateless & multi-instance.
kwargs = dict(
    agents_dir=AGENTS_DIR,
    web=True,
    port=PORT,
    extra_plugins=extra_plugins,
    trace_to_cloud=os.environ.get("TRACE_TO_CLOUD", "off").lower() == "on",
)
if os.environ.get("SESSION_SERVICE_URI"):
    kwargs["session_service_uri"] = os.environ["SESSION_SERVICE_URI"]
if os.environ.get("MEMORY_SERVICE_URI"):
    kwargs["memory_service_uri"] = os.environ["MEMORY_SERVICE_URI"]

app = get_fast_api_app(**kwargs)


if __name__ == "__main__":
    # 0.0.0.0 so a container accepts external traffic on Cloud Run.
    uvicorn.run(app, host="0.0.0.0", port=PORT)
