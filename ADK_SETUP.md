# ADK Implementation Setup Guide

This guide walks you through setting up and running the Google ADK implementation of the Customer Refund Agent with Gemini 2.5 Pro.

## Prerequisites

- Python 3.11+
- GCP Account with `linkhealth-care-2024` project
- Google Cloud CLI installed
- Access to Gemini 2.5 Pro API

## Step 1: GCP Project Setup

### 1.1 Enable Required APIs

```bash
gcloud config set project linkhealth-care-2024

# Enable Gemini API
gcloud services enable generativeaiapi.googleapis.com

# Enable other required services
gcloud services enable aiplatform.googleapis.com
gcloud services enable cloudruntime.googleapis.com
```

### 1.2 Create Service Account

```bash
# Create service account
gcloud iam service-accounts create refund-agent-sa \
  --display-name="Refund Agent Service Account"

# Grant permissions
gcloud projects add-iam-policy-binding linkhealth-care-2024 \
  --member=serviceAccount:refund-agent-sa@linkhealth-care-2024.iam.gserviceaccount.com \
  --role=roles/aiplatform.user

# Create and download key
gcloud iam service-accounts keys create ~/gcp-refund-agent-key.json \
  --iam-account=refund-agent-sa@linkhealth-care-2024.iam.gserviceaccount.com

# Set permissions
chmod 600 ~/gcp-refund-agent-key.json
```

## Step 2: Local Development Setup

### 2.1 Install Dependencies

```bash
cd adk_refund

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install package and dependencies
pip install -e .
```

### 2.2 Configure Environment

```bash
# Copy template
cp .env.example .env

# Edit .env with your credentials
nano .env
```

Update `.env`:
```bash
GOOGLE_CLOUD_PROJECT=linkhealth-care-2024
GOOGLE_APPLICATION_CREDENTIALS=/Users/fmlin/gcp-refund-agent-key.json
GENAI_API_KEY=<your-gemini-api-key>
ADK_MODEL=gemini-2.5-pro
```

### 2.3 Verify Setup

```bash
# Test GCP authentication
python -c "from google.auth import default; creds, proj = default(); print(f'✓ Project: {proj}')"

# Test Gemini API
python -c "from google import genai; client = genai.Client(); print('✓ Gemini API ready')"
```

## Step 3: Run Test Scenarios

### 3.1 Run Single Scenario

```bash
cd adk_refund

# Scenario 1: Auto-Approve (happy path)
python run_refund.py scenario-1-auto-approve

# Scenario 2: Past Refund Window (escalate)
python run_refund.py scenario-2-past-window

# Scenario 3: In Transit (escalate)
python run_refund.py scenario-3-in-transit
```

### 3.2 Run All 7 Scenarios

```bash
for scenario in scenario-1-auto-approve scenario-2-past-window scenario-3-in-transit \
                scenario-4-not-found scenario-5-high-value scenario-6-duplicate scenario-7-fraud-risk; do
  echo "Running $scenario..."
  python run_refund.py $scenario "batch-run-$(date +%s)"
done
```

### 3.3 View Results

```bash
# View pipeline output
cat output/refund-demo-01/pipeline-output.json | jq '.'

# Check specific stage
cat output/refund-demo-01/order-lookup/order-lookup.txt
```

## Step 4: Deploy to Google Cloud

### 4.1 Build Docker Image

```bash
# Create Dockerfile
cat > adk_refund/Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install -e .

COPY refund_agent/ refund_agent/
COPY data/ data/
COPY run_refund.py .

ENV PYTHONUNBUFFERED=1
CMD ["python", "run_refund.py", "scenario-1-auto-approve"]
EOF

# Build image
gcloud builds submit --tag gcr.io/linkhealth-care-2024/refund-agent adk_refund/
```

### 4.2 Deploy to Cloud Run

```bash
gcloud run deploy refund-agent \
  --image gcr.io/linkhealth-care-2024/refund-agent \
  --platform managed \
  --region us-central1 \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=linkhealth-care-2024" \
  --service-account refund-agent-sa@linkhealth-care-2024.iam.gserviceaccount.com
```

### 4.3 Deploy to Vertex AI

```bash
# Create custom training job
gcloud ai custom-jobs create \
  --display-name refund-agent-training \
  --worker-pool-spec \
    machine-type=n1-standard-4,\
    replica-count=1,\
    container-image-uri=gcr.io/linkhealth-care-2024/refund-agent
```

## Step 5: Production Configuration

### 5.1 Firestore Integration (Optional)

For persistent state storage:

```bash
# Enable Firestore
gcloud services enable firestore.googleapis.com

# Create Firestore database
gcloud firestore databases create --location=us-central1
```

Update `run_refund.py`:
```python
from google.adk.sessions import FirestoreSessionService

session_service = FirestoreSessionService(
    project_id="linkhealth-care-2024",
    collection_path="refund_sessions"
)
```

### 5.2 Cloud Logging Integration

```bash
# Enable Cloud Logging
gcloud services enable logging.googleapis.com

# Logs will automatically be sent to Cloud Logging
```

### 5.3 Set Up Monitoring

```bash
# View logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=refund-agent"

# Create alert policy (optional)
gcloud alpha monitoring policies create \
  --notification-channels=<CHANNEL_ID> \
  --display-name="Refund Agent Error Rate"
```

## Troubleshooting

### Issue: `ModuleNotFoundError: No module named google.adk`

**Solution:**
```bash
pip install google-adk>=1.31.0 google-genai>=1.0.0
```

### Issue: `GOOGLE_APPLICATION_CREDENTIALS not found`

**Solution:**
```bash
# Verify key file exists
ls -la ~/gcp-refund-agent-key.json

# Set environment variable
export GOOGLE_APPLICATION_CREDENTIALS=/Users/fmlin/gcp-refund-agent-key.json
```

### Issue: `Permission denied: Gemini API`

**Solution:**
```bash
# Enable API
gcloud services enable generativeaiapi.googleapis.com

# Check service account has IAM role
gcloud projects get-iam-policy linkhealth-care-2024 \
  --flatten="bindings[].members" \
  --filter="bindings.members:refund-agent-sa*"
```

### Issue: `No module named refund_agent`

**Solution:**
```bash
# Make sure you're in adk_refund directory
cd adk_refund

# Reinstall in development mode
pip install -e .
```

## Development Workflow

### 1. Make Changes

Edit `refund_agent/skills.py`, `agent.py`, etc.

### 2. Test Locally

```bash
python run_refund.py scenario-1-auto-approve
```

### 3. Check Output

```bash
cat output/refund-demo-01/pipeline-output.json | jq '.stages | keys'
```

### 4. Commit and Push

```bash
git add -A
git commit -m "feat: update ADK implementation"
git push origin main
```

### 5. Rebuild and Redeploy

```bash
gcloud builds submit --tag gcr.io/linkhealth-care-2024/refund-agent adk_refund/

gcloud run deploy refund-agent \
  --image gcr.io/linkhealth-care-2024/refund-agent
```

## API Reference

### SequentialAgent Pipeline

```python
from refund_agent.agent import build_pipeline

pipeline = build_pipeline(run_name="refund-demo-01")
# Agents execute in sequence:
# 1. order-lookup
# 2. refund-decision
# 3. fraud-detection
# 4. customer-communication
```

### Session State

Each agent has access to previous stage outputs via `ctx.state`:

```python
def get_instruction(ctx):
    order_data = ctx.state.get("order_lookup_output")
    decision_data = ctx.state.get("refund_decision_output")
    # ... use in prompt
```

### Output Capture

Pipeline outputs automatically saved to:
```
output/{run_name}/pipeline-output.json
```

## Next Steps

1. ✅ Local testing with 7 scenarios
2. ✅ Deploy to Cloud Run
3. [ ] Set up real Firestore backend
4. [ ] Add API gateway for REST access
5. [ ] Integrate with ticketing system (Jira/Linear)
6. [ ] Add monitoring dashboards
7. [ ] Enable multi-tenant support

---

**GCP Project:** linkhealth-care-2024  
**Model:** Gemini 2.5 Pro  
**SDK:** Google ADK 1.31.0+  
**Python:** 3.11+
