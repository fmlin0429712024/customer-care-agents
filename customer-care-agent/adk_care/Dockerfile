FROM python:3.12-slim

WORKDIR /app
COPY . /app

# Install the coordinator's runtime deps (ADK + A2A + trace exporter).
RUN pip install --no-cache-dir -r requirements.txt

# Non-secret defaults. On deploy, set:
#   REFUND_A2A_BASE_URL = the worker's Cloud Run URL (e.g. https://refund-agent-...run.app)
#   TRACE_TO_CLOUD      = on
#   SESSION_SERVICE_URI / MEMORY_SERVICE_URI = durable backends (stateless runtime)
ENV PII_GUARDRAIL=on \
    TRACE_TO_CLOUD=on

# serve.py reads $PORT and binds 0.0.0.0.
CMD ["python", "serve.py"]
