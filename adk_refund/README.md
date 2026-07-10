# Customer Refund Agent — Google ADK Implementation

Production-ready ADK implementation of the customer refund processing pipeline using Gemini 2.5 Pro on Google Cloud.

## Quick Start

### 1. Setup

```bash
# Create Python environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
cd adk_refund
pip install -e .

# Configure GCP credentials
cp .env.example .env
# Edit .env with your GCP project and credentials
```

### 2. Set GCP Credentials

```bash
# Option A: Service Account Key (local development)
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/gcp-service-account-key.json

# Option B: Application Default Credentials (production)
gcloud auth application-default login
```

### 3. Run a Scenario

```bash
# Run scenario 1 (auto-approve)
python run_refund.py scenario-1-auto-approve

# Run scenario 2 with custom run name
python run_refund.py scenario-2-past-window refund-run-02

# List available scenarios
ls data/scenario-*/
```

## Pipeline Stages

```
Order Lookup (verify + extract)
    ↓
Refund Decision (apply rules)
    ↓
Fraud Detection (screen for abuse)
    ↓
Customer Communication (craft response)
```

## Test Scenarios

| # | Scenario | Expected Decision | Reason Code |
|---|----------|-------------------|------------|
| 1 | scenario-1-auto-approve | APPROVE | AUTO_APPROVED |
| 2 | scenario-2-past-window | ESCALATE | PAST_REFUND_WINDOW |
| 3 | scenario-3-in-transit | ESCALATE | IN_TRANSIT |
| 4 | scenario-4-not-found | REJECT | ORDER_NOT_FOUND |
| 5 | scenario-5-high-value | ESCALATE | HIGH_VALUE_ORDER |
| 6 | scenario-6-duplicate | ESCALATE | DUPLICATE_REFUND |
| 7 | scenario-7-fraud-risk | ESCALATE | FRAUD_RISK |

## Project Structure

```
adk_refund/
├── refund_agent/
│   ├── __init__.py
│   ├── agent.py              # ADK agent definitions
│   └── tools.py              # Tools and data loading
├── data/
│   ├── scenario-1-auto-approve/
│   ├── scenario-2-past-window/
│   ├── scenario-3-in-transit/
│   ├── scenario-4-not-found/
│   ├── scenario-5-high-value/
│   ├── scenario-6-duplicate/
│   └── scenario-7-fraud-risk/
├── output/                   # Pipeline outputs saved here
├── .env.example              # Environment template
├── pyproject.toml
├── run_refund.py             # Main entry point
└── README.md
```

## Environment Variables

```bash
GOOGLE_CLOUD_PROJECT=linkhealth-care-2024
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
GENAI_API_KEY=your-gemini-api-key
ADK_MODEL=gemini-2.5-pro
```

## How It Works

### 1. Order Lookup Stage
- Verifies order exists in reference data
- Extracts order details (amount, status, delivery date)
- Calculates days since delivery
- Outputs: ORDER LOOKUP RESULT

### 2. Refund Decision Stage
- Loads refund policy rules
- Applies eligibility checks (5-day window, $500 cap, delivery status)
- Produces decision: APPROVE / ESCALATE / REJECT
- Outputs: REFUND DECISION with reason code

### 3. Fraud Detection Stage
- Screens tentative APPROVEs for abuse patterns
- Checks: duplicate refunds, refund frequency (>3 in 30 days)
- May override APPROVE → ESCALATE if flags detected
- Outputs: FRAUD SCREEN RESULT

### 4. Customer Communication Stage
- Reads all previous stage outputs
- Crafts appropriate customer-facing message
- Tone varies by outcome: celebratory (APPROVE), empathetic (ESCALATE), helpful (REJECT)
- Outputs: Customer response ready to send

## Outputs

Each run saves outputs to `output/{run_name}/`:
- `pipeline-output.json` — Full pipeline results with all stages
- Stage-specific files — Detailed output from each agent

## Integration with Cloud Firestore

To enable persistent state (future):

```python
from google.adk.sessions import FirestoreSessionService

session_service = FirestoreSessionService(
    project_id="linkhealth-care-2024",
    collection_path="refund_sessions"
)
```

## Production Deployment

### Google Cloud Run

```bash
# Build container
gcloud builds submit --tag gcr.io/linkhealth-care-2024/refund-agent

# Deploy
gcloud run deploy refund-agent \
  --image gcr.io/linkhealth-care-2024/refund-agent \
  --platform managed \
  --region us-central1 \
  --set-env-vars GOOGLE_CLOUD_PROJECT=linkhealth-care-2024
```

### Vertex AI Integration

The agent can be deployed as a Vertex AI custom training job:

```bash
gcloud ai custom-jobs create \
  --display-name refund-agent \
  --python-image gcr.io/linkhealth-care-2024/refund-agent
```

## Troubleshooting

### `ModuleNotFoundError: No module named google.adk`
```bash
pip install google-adk>=1.31.0
```

### `GOOGLE_APPLICATION_CREDENTIALS not found`
```bash
# Download service account key from GCP Console
# https://console.cloud.google.com/iam-admin/serviceaccounts
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
```

### `Permission denied: Gemini API`
```bash
# Enable Gemini API in GCP Console
gcloud services enable generativeaiapi.googleapis.com
```

## Development

### Run Tests
```bash
pytest tests/ -v
```

### Add New Scenario
1. Create folder: `data/scenario-{name}/`
2. Add `details.json` with order data and expected outcome
3. Run: `python run_refund.py scenario-{name}`

### Extend Pipeline
1. Create new agent in `refund_agent/agent.py`
2. Add to `build_pipeline()` SequentialAgent list
3. New agent can access previous stage outputs via `ctx.state`

## Status

- **v0.1.0** — Initial ADK implementation with 4 main stages and 7 test scenarios
- **Next**: Firestore integration, Cloud Run deployment, multi-tenant support

---

**Repository:** https://github.com/fmlin0429712024/customer-refund-agent  
**GCP Project:** linkhealth-care-2024  
**Model:** Gemini 2.5 Pro
