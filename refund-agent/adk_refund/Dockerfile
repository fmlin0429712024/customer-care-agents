FROM python:3.12-slim

WORKDIR /app
COPY . /app

# Install the agent package + A2A extras + the two OTel exporters.
RUN pip install --no-cache-dir -e . \
    "google-adk[a2a]" "a2a-sdk[http-server]" \
    "opentelemetry-exporter-gcp-trace==1.12.0" \
    "opentelemetry-exporter-otlp-proto-http==1.42.1"

# Non-secret defaults. Secrets (API keys) are injected at deploy time.
# A2A_PUBLIC_URL is set at deploy so the Agent Card advertises the public URL.
ENV PII_GUARDRAIL=on \
    REFUND_DB_PATH=/tmp/refund.db

# A2A endpoint (the service the coordinator calls). a2a_server.py binds
# 0.0.0.0:$PORT. For the local playground instead, run serve_dual_trace.py.
CMD ["python", "a2a_server.py"]
