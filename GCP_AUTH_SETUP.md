# GCP Authentication Setup — Manual Steps Required

**Important:** Claude (me) cannot directly authenticate with GCP. You must complete these steps manually on your laptop.

## Overview

Your ADK app needs two authentication methods:
1. **Service Account Key** — for API access (long-lived credentials)
2. **gcloud CLI** — for Cloud deployment (user sign-on)

---

## Step 1: Install Google Cloud CLI

### macOS

```bash
# Install gcloud CLI
curl https://sdk.cloud.google.com | bash

# Restart shell or reload path
exec -l $SHELL

# Verify installation
gcloud --version
```

### Verify

```bash
gcloud --version
# Should show: Google Cloud SDK X.X.X
```

---

## Step 2: Create Service Account for Local Development

**You must approve this in GCP Console.**

### 2.1 Set Project

```bash
gcloud config set project linkhealth-care-2024
gcloud config list
# Should show: project = linkhealth-care-2024
```

### 2.2 Create Service Account

```bash
gcloud iam service-accounts create refund-agent-dev \
  --display-name="Refund Agent — Local Development"

# Verify
gcloud iam service-accounts list
# Should show: refund-agent-dev@linkhealth-care-2024.iam.gserviceaccount.com
```

### 2.3 Grant Permissions

```bash
gcloud projects add-iam-policy-binding linkhealth-care-2024 \
  --member=serviceAccount:refund-agent-dev@linkhealth-care-2024.iam.gserviceaccount.com \
  --role=roles/aiplatform.user

# Verify
gcloud projects get-iam-policy linkhealth-care-2024 \
  --flatten="bindings[].members" \
  --filter="bindings.members:refund-agent-dev*"
```

### 2.4 Create & Download Private Key

**⚠️ This is your sensitive credential — keep it safe!**

```bash
# Create key
gcloud iam service-accounts keys create ~/gcp-refund-agent-key.json \
  --iam-account=refund-agent-dev@linkhealth-care-2024.iam.gserviceaccount.com

# Set restrictive permissions
chmod 600 ~/gcp-refund-agent-key.json

# Verify file exists (don't share the content!)
ls -la ~/gcp-refund-agent-key.json
# Should show: -rw------- (only you can read)
```

---

## Step 3: Get Gemini API Key

### 3.1 Enable Gemini API

```bash
gcloud services enable generativeaiapi.googleapis.com

# Verify
gcloud services list --enabled | grep generative
```

### 3.2 Create API Key

```bash
# Go to GCP Console
# https://console.cloud.google.com/apis/credentials

# Or use CLI (if available in your project)
gcloud alpha services api-keys create \
  --display-name="Gemini API Key" \
  --project=linkhealth-care-2024

# Copy the key value
```

**Alternative:** Use service account credentials directly (already created above)

---

## Step 4: Configure Local .env File

```bash
cd adk_refund

# Create .env from template
cp .env.example .env

# Edit with your credentials
nano .env
```

Add these values:

```bash
# ✅ Required
GOOGLE_CLOUD_PROJECT=linkhealth-care-2024
GOOGLE_APPLICATION_CREDENTIALS=/Users/fmlin/gcp-refund-agent-key.json
GENAI_API_KEY=<paste-your-api-key-here>

# ✅ Optional (defaults to gemini-2.5-pro)
ADK_MODEL=gemini-2.5-pro
```

**⚠️ Never commit .env to GitHub** (it's in .gitignore ✓)

---

## Step 5: Verify Authentication

### 5.1 Test Service Account

```bash
cd adk_refund

export GOOGLE_APPLICATION_CREDENTIALS=/Users/fmlin/gcp-refund-agent-key.json

# Test authentication
python3 -c "
from google.auth import default
creds, project = default()
print(f'✓ Authenticated')
print(f'✓ Project: {project}')
print(f'✓ Service Account: {creds.service_account_email}')
"

# Should output:
# ✓ Authenticated
# ✓ Project: linkhealth-care-2024
# ✓ Service Account: refund-agent-dev@linkhealth-care-2024.iam.gserviceaccount.com
```

### 5.2 Test Gemini API

```bash
# Load .env
source .env

# Test Gemini connection
python test_gemini.py

# Should output:
# ✓ google-genai imported
# ✓ Gemini client created
# ✓ gemini-2.5-pro is available
# ✓ ALL TESTS PASSED
```

### 5.3 Test Full Setup

```bash
bash check_setup.sh

# Should show:
# [1] Python Version — ✓ Python 3.11+
# [2] Virtual Environment — ✓ venv activated
# [3] Required Packages — ✓ All packages installed
# [4] Environment Configuration — ✓ .env file configured
# [5] GCP Authentication — ✓ Credentials valid
# [6] Test Data — ✓ All scenarios found
# [7] Python Imports — ✓ refund_agent imports OK
```

---

## Step 6: Run First Scenario

```bash
python run_refund.py scenario-1-auto-approve

# Should show:
# CUSTOMER REFUND PIPELINE — ADK IMPLEMENTATION
# ====================================================================
# Scenario    : scenario-1-auto-approve
# Run name    : refund-demo-01
# Order ID    : 67890
# Expected    : APPROVE — AUTO_APPROVED
# ====================================================================

# [Agent 1: order-lookup output...]
# [Agent 2: refund-decision output...]
# [Agent 3: fraud-detection output...]
# [Agent 4: customer-communication output...]

# ✓ Pipeline complete
# ✓ Output saved to: output/refund-demo-01/pipeline-output.json
```

---

## What Each Credential Does

| Credential | Purpose | Location | Risk |
|------------|---------|----------|------|
| Service Account Key JSON | API authentication for ADK | `~/gcp-refund-agent-key.json` | HIGH — Never share |
| Gemini API Key | Gemini model access | `.env` (GENAI_API_KEY) | HIGH — Never commit |
| gcloud CLI config | Cloud deployment & management | `~/.config/gcloud/` | MEDIUM — Limited scope |

---

## Security Checklist

- [ ] Service account key downloaded and stored locally
- [ ] Key file permissions set to 600 (readable only by you)
- [ ] `.env` file created with credentials
- [ ] `.env` is in `.gitignore` (cannot be committed)
- [ ] `.env` is NOT shared via Slack/email/etc
- [ ] `test_gemini.py` runs successfully
- [ ] `check_setup.sh` shows all checks passed

---

## Troubleshooting

### Issue: `Permission denied: User [email] does not have permission`

**Solution:**
```bash
# Grant additional permissions
gcloud projects add-iam-policy-binding linkhealth-care-2024 \
  --member=serviceAccount:refund-agent-dev@linkhealth-care-2024.iam.gserviceaccount.com \
  --role=roles/compute.admin

# Or use broader role for development:
--role=roles/editor  # Use only for dev, not production
```

### Issue: `GOOGLE_APPLICATION_CREDENTIALS not found`

**Solution:**
```bash
# Check file exists
ls -la ~/gcp-refund-agent-key.json

# Set environment variable before running
export GOOGLE_APPLICATION_CREDENTIALS=/Users/fmlin/gcp-refund-agent-key.json

# Or add to .env (persistent)
echo "GOOGLE_APPLICATION_CREDENTIALS=/Users/fmlin/gcp-refund-agent-key.json" >> .env
```

### Issue: `Invalid API key`

**Solution:**
```bash
# Verify API key in GCP Console
# https://console.cloud.google.com/apis/credentials

# Make sure it's for the correct project (linkhealth-care-2024)
# Copy fresh and update .env
```

### Issue: `Gemini API is not enabled`

**Solution:**
```bash
gcloud services enable generativeaiapi.googleapis.com

# Wait a few seconds for service to initialize
sleep 5

# Test again
python test_gemini.py
```

---

## Manual Setup Checklist

- [ ] Step 1: Google Cloud CLI installed and verified
- [ ] Step 2: Service account created (refund-agent-dev)
- [ ] Step 2.3: IAM role granted to service account
- [ ] Step 2.4: Private key downloaded to `~/gcp-refund-agent-key.json`
- [ ] Step 3: Gemini API enabled
- [ ] Step 3.2: API key created and copied
- [ ] Step 4: `.env` file created with all credentials
- [ ] Step 5.1: Service account authentication verified
- [ ] Step 5.2: Gemini API connection verified
- [ ] Step 5.3: Full setup check passed
- [ ] Step 6: First scenario runs successfully

---

## What Happens Next

Once all steps above are complete:

```bash
# Your ADK agent can now:
cd adk_refund
python run_refund.py scenario-1-auto-approve

# Each run will:
# 1. Load .env credentials
# 2. Authenticate with GCP
# 3. Call Gemini 2.5 Pro API
# 4. Process refund through 4-stage pipeline
# 5. Save output to JSON
# 6. Exit successfully
```

---

**Ready to start?** Begin with **Step 1: Install Google Cloud CLI**

Then come back and let me know when you've completed all 6 steps!
