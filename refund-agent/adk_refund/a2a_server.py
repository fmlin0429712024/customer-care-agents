"""Expose the refund worker as an A2A server — WITH the full harness.

Cloud-Run-ready A2A endpoint that now carries the SAME harness as the playground
(`serve_dual_trace.py`): PII **guardrail** + OpenTelemetry **tracing**. Both attach
at the serve layer; the worker's `agent.py` / `SKILL.md` are untouched.

Two attach points (this is the whole lesson of "harness lives on the serve entry"):

  1. GUARDRAIL → a custom `Runner(plugins=[PIIRedactionPlugin])` **overrides** the
     bare default Runner that `to_a2a` would build (that default has no plugins),
     so the `before_model` hook fires on the worker's model calls too.

  2. TRACE → the GLOBAL OTel `TracerProvider` is configured BEFORE the app is
     built, so ADK's spans get exported. ADK always *emits* spans (instrumentation
     is built in); without an exporter they are just dropped. We attach an
     exporter — Console locally (`OTEL_CONSOLE=on`), Cloud Trace in the container.

Local:      OTEL_CONSOLE=on python a2a_server.py      # binds 0.0.0.0:8043
Cloud Run:  set A2A_PUBLIC_URL so the Agent Card advertises the public URL.
"""

import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

# Load Vertex + Firestore env BEFORE importing the agent (tools.py builds a
# Firestore client at import time).
load_dotenv(Path(__file__).parent / "refund_agent" / ".env")

# --- TRACE: configure the GLOBAL OTel provider BEFORE the app is built --------
from opentelemetry import trace  # noqa: E402
from opentelemetry.sdk.resources import Resource  # noqa: E402
from opentelemetry.sdk.trace import TracerProvider  # noqa: E402
from opentelemetry.sdk.trace.export import (  # noqa: E402
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)


def _build_tracer_provider() -> TracerProvider:
    """One provider, one or more exporters — this is the whole trace 'integration'."""
    provider = TracerProvider(
        resource=Resource.create({"service.name": "refund_agent_a2a"})
    )
    # Cloud Trace (container has the exporter; local venv usually does not).
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if project:
        try:
            from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter

            provider.add_span_processor(
                BatchSpanProcessor(CloudTraceSpanExporter(project_id=project))
            )
            print(f"[otel] Cloud Trace exporter -> project {project}")
        except ImportError:
            print("[otel] cloud-trace exporter not installed — skipping")
    # Console exporter: prints spans locally so you can SEE tracing work.
    if os.environ.get("OTEL_CONSOLE", "off").lower() == "on":
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
        print("[otel] Console exporter ON (spans print to stdout)")
    return provider


if os.environ.get("TRACE", "on").lower() != "off":
    trace.set_tracer_provider(_build_tracer_provider())

# --- GUARDRAIL: build a custom Runner that carries the PII plugin --------------
from google.adk.a2a.utils.agent_to_a2a import to_a2a  # noqa: E402
from google.adk.artifacts.in_memory_artifact_service import (  # noqa: E402
    InMemoryArtifactService,
)
from google.adk.auth.credential_service.in_memory_credential_service import (  # noqa: E402
    InMemoryCredentialService,
)
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService  # noqa: E402
from google.adk.runners import Runner  # noqa: E402
from google.adk.sessions.in_memory_session_service import InMemorySessionService  # noqa: E402

from guardrails import PIIRedactionPlugin  # noqa: E402
from refund_agent.agent import root_agent  # noqa: E402

_plugins = []
if os.environ.get("PII_GUARDRAIL", "on").lower() != "off":
    _plugins = [PIIRedactionPlugin()]
    print("[guardrail] refund A2A PII redaction ENABLED")

# Same in-memory services to_a2a would create by default, PLUS our plugins.
# Passing this as `runner=` overrides to_a2a's bare default Runner, so the
# guardrail hook fires on the worker's model calls.
_runner = Runner(
    app_name=root_agent.name or "refund_agent",
    agent=root_agent,
    artifact_service=InMemoryArtifactService(),
    session_service=InMemorySessionService(),
    memory_service=InMemoryMemoryService(),
    credential_service=InMemoryCredentialService(),
    plugins=_plugins,
)

PORT = int(os.environ.get("PORT", "8043"))
_public = os.environ.get("A2A_PUBLIC_URL")
if _public:
    u = urlparse(_public)
    _proto = u.scheme or "https"
    a2a_app = to_a2a(
        root_agent,
        runner=_runner,
        host=u.hostname,
        port=u.port or (443 if _proto == "https" else 80),
        protocol=_proto,
    )
else:
    a2a_app = to_a2a(root_agent, runner=_runner, port=PORT)


if __name__ == "__main__":
    import uvicorn

    # 0.0.0.0 so a container accepts external traffic on Cloud Run.
    uvicorn.run(a2a_app, host="0.0.0.0", port=PORT)
