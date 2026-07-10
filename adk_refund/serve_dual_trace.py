"""Launch the ADK playground with DUAL trace export: GCP Cloud Trace + LangSmith.

This file is pure host wiring — it does NOT import or modify agent.py, tools.py,
or any SKILL.md. It only configures the global OpenTelemetry TracerProvider with
two exporters, then serves the same ADK app you already run with `adk web`.

This is the concrete answer to "how does OTel setup work on the app side":
ADK emits spans into the GLOBAL TracerProvider; we attach two exporters to it,
so every span fans out to both backends. Adding/removing a backend never touches
business logic.

Run:
    export GOOGLE_CLOUD_PROJECT=linkhealth-care-2024
    export LANGSMITH_API_KEY=ls-...            # from smith.langchain.com
    export LANGSMITH_PROJECT=refund-agent      # optional, defaults below
    python serve_dual_trace.py

Then open http://127.0.0.1:8001 — traffic shows up in BOTH GCP Trace Explorer
and LangSmith. If LANGSMITH_API_KEY is unset, it exports to Cloud Trace only.
"""

import os
from pathlib import Path

import uvicorn
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

PORT = int(os.environ.get("PORT", 8001))  # Cloud Run injects $PORT
AGENTS_DIR = str(Path(__file__).parent)  # contains the refund_agent/ package


def build_tracer_provider() -> TracerProvider:
    """One provider, up to two exporters. This is the whole 'integration'."""
    provider = TracerProvider(
        resource=Resource.create({"service.name": "refund_agent"})
    )

    # --- Exporter 1: GCP Cloud Trace ---------------------------------------
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if project:
        provider.add_span_processor(
            BatchSpanProcessor(CloudTraceSpanExporter(project_id=project))
        )
        print(f"[otel] Cloud Trace exporter -> project {project}")
    else:
        print("[otel] GOOGLE_CLOUD_PROJECT unset — skipping Cloud Trace")

    # --- Exporter 2: LangSmith (via standard OTLP/HTTP) --------------------
    ls_key = os.environ.get("LANGSMITH_API_KEY")
    if ls_key:
        ls_project = os.environ.get("LANGSMITH_PROJECT", "refund-agent")
        provider.add_span_processor(
            BatchSpanProcessor(
                OTLPSpanExporter(
                    endpoint="https://api.smith.langchain.com/otel/v1/traces",
                    headers={
                        "x-api-key": ls_key,
                        "Langsmith-Project": ls_project,
                    },
                )
            )
        )
        print(f"[otel] LangSmith OTLP exporter -> project '{ls_project}'")
    else:
        print("[otel] LANGSMITH_API_KEY unset — skipping LangSmith")

    return provider


# Set the GLOBAL provider BEFORE building the ADK app, so ADK's spans (created
# via trace.get_tracer(...)) flow into our two exporters.
trace.set_tracer_provider(build_tracer_provider())

from google.adk.cli.fast_api import get_fast_api_app  # noqa: E402

# Governance layer: PII redaction guardrail, injected as a Plugin at the serve
# layer — never in agent.py / SKILL.md. Toggle with PII_GUARDRAIL=off.
# ADK's extra_plugins wants fully-qualified names (it imports + instantiates).
extra_plugins = None
if os.environ.get("PII_GUARDRAIL", "on").lower() != "off":
    extra_plugins = ["guardrails.PIIRedactionPlugin"]
    print("[guardrail] PII redaction ENABLED")
else:
    print("[guardrail] PII redaction OFF")

# trace_to_cloud=False: we manage Cloud Trace ourselves above, so ADK does not
# install a second/competing provider.
app = get_fast_api_app(
    agents_dir=AGENTS_DIR,
    web=True,
    trace_to_cloud=False,
    port=PORT,
    extra_plugins=extra_plugins,
)


if __name__ == "__main__":
    # 0.0.0.0 so the container accepts external traffic on Cloud Run.
    uvicorn.run(app, host="0.0.0.0", port=PORT)
