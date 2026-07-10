FROM python:3.12-slim

WORKDIR /app
COPY . /app

# Install the agent package + the two OTel exporters (trace path only).
RUN pip install --no-cache-dir -e . \
    "opentelemetry-exporter-gcp-trace==1.12.0" \
    "opentelemetry-exporter-otlp-proto-http==1.42.1"

# Non-secret defaults. Secrets (API keys) are injected at deploy time.
ENV PII_GUARDRAIL=on \
    REFUND_DB_PATH=/tmp/refund.db

# serve_dual_trace.py reads $PORT and binds 0.0.0.0.
CMD ["python", "serve_dual_trace.py"]
