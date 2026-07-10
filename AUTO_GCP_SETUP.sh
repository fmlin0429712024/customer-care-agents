#!/bin/bash
# AUTOMATED GCP SETUP — Run this in your local terminal
# This script will handle everything, including the login prompt

set -e

GCP_PROJECT="linkhealth-care-2024"
SERVICE_ACCOUNT="refund-agent-dev"
KEY_FILE="$HOME/gcp-refund-agent-key.json"
ADK_DIR="/Users/fmlin/Documents/customer-refund-agent/adk_refund"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║         AUTOMATED GCP SETUP FOR REFUND AGENT               ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Project: $GCP_PROJECT"
echo "Service Account: $SERVICE_ACCOUNT"
echo "Key File: $KEY_FILE"
echo ""

# ============================================================================
# STEP 1: Verify gcloud is installed
# ============================================================================
echo "[1/8] Checking gcloud CLI..."
if ! command -v gcloud &> /dev/null; then
    echo "✗ gcloud CLI not found"
    echo "Please install: curl https://sdk.cloud.google.com | bash"
    exit 1
fi
echo "✓ gcloud CLI found: $(gcloud --version | head -1)"

# ============================================================================
# STEP 2: Interactive Login (USER APPROVAL REQUIRED)
# ============================================================================
echo ""
echo "[2/8] GCP Authentication..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚠️  A browser window will open — you need to APPROVE login"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if already authenticated
CURRENT_ACCOUNT=$(gcloud config get-value account 2>/dev/null || echo "none")
if [[ "$CURRENT_ACCOUNT" != "none" ]]; then
    echo "Current account: $CURRENT_ACCOUNT"
    read -p "Use this account? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        gcloud auth login
    fi
else
    echo "No account authenticated. Opening browser for login..."
    gcloud auth login
fi

CURRENT_ACCOUNT=$(gcloud config get-value account)
echo "✓ Authenticated as: $CURRENT_ACCOUNT"

# ============================================================================
# STEP 3: Set default project
# ============================================================================
echo ""
echo "[3/8] Setting default GCP project..."
gcloud config set project $GCP_PROJECT
CONFIGURED_PROJECT=$(gcloud config get-value project)
echo "✓ Project set to: $CONFIGURED_PROJECT"

# ============================================================================
# STEP 4: Enable APIs
# ============================================================================
echo ""
echo "[4/8] Enabling required APIs..."
echo "  Enabling generativeaiapi..."
gcloud services enable generativeaiapi.googleapis.com
echo "  Enabling aiplatform..."
gcloud services enable aiplatform.googleapis.com
echo "✓ APIs enabled"

# ============================================================================
# STEP 5: Create service account (or verify existing)
# ============================================================================
echo ""
echo "[5/8] Creating service account..."
SERVICE_ACCOUNT_FULL="$SERVICE_ACCOUNT@$GCP_PROJECT.iam.gserviceaccount.com"

if gcloud iam service-accounts describe $SERVICE_ACCOUNT_FULL &>/dev/null 2>&1; then
    echo "✓ Service account already exists: $SERVICE_ACCOUNT_FULL"
else
    echo "  Creating new service account..."
    gcloud iam service-accounts create $SERVICE_ACCOUNT \
        --display-name="Refund Agent — Local Development"
    echo "✓ Service account created: $SERVICE_ACCOUNT_FULL"
fi

# ============================================================================
# STEP 6: Grant IAM role
# ============================================================================
echo ""
echo "[6/8] Granting IAM permissions..."
gcloud projects add-iam-policy-binding $GCP_PROJECT \
    --member=serviceAccount:$SERVICE_ACCOUNT_FULL \
    --role=roles/aiplatform.user \
    --quiet 2>/dev/null || true
echo "✓ IAM role granted"

# ============================================================================
# STEP 7: Create/download service account key
# ============================================================================
echo ""
echo "[7/8] Creating service account key..."

if [[ -f "$KEY_FILE" ]]; then
    echo "⚠️  Key file already exists: $KEY_FILE"
    read -p "Regenerate? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        gcloud iam service-accounts keys create $KEY_FILE \
            --iam-account=$SERVICE_ACCOUNT_FULL
        chmod 600 $KEY_FILE
        echo "✓ Key regenerated: $KEY_FILE"
    else
        echo "✓ Using existing key: $KEY_FILE"
    fi
else
    gcloud iam service-accounts keys create $KEY_FILE \
        --iam-account=$SERVICE_ACCOUNT_FULL
    chmod 600 $KEY_FILE
    echo "✓ Key created: $KEY_FILE"
fi

# Verify file permissions
PERMS=$(ls -l $KEY_FILE | awk '{print $1}')
echo "  File permissions: $PERMS (should be -rw------)"

# ============================================================================
# STEP 8: Create/update .env file
# ============================================================================
echo ""
echo "[8/8] Configuring .env file..."

if [[ ! -f "$ADK_DIR/.env" ]]; then
    cp "$ADK_DIR/.env.example" "$ADK_DIR/.env"
    echo "✓ .env file created from template"
fi

# Update .env with credentials
sed -i '' "s|GOOGLE_CLOUD_PROJECT=.*|GOOGLE_CLOUD_PROJECT=$GCP_PROJECT|" "$ADK_DIR/.env"
sed -i '' "s|GOOGLE_APPLICATION_CREDENTIALS=.*|GOOGLE_APPLICATION_CREDENTIALS=$KEY_FILE|" "$ADK_DIR/.env"

echo "✓ .env updated with GCP credentials"

# ============================================================================
# VERIFICATION
# ============================================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "VERIFYING AUTHENTICATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

export GOOGLE_APPLICATION_CREDENTIALS=$KEY_FILE

python3 << 'VERIFY_SCRIPT'
import os
try:
    from google.auth import default
    creds, project = default()
    print(f"✓ Service account authenticated")
    print(f"  Project: {project}")
    print(f"  Account: {creds.service_account_email}")
except Exception as e:
    print(f"✗ Authentication failed: {e}")
    exit(1)
VERIFY_SCRIPT

if [ $? -ne 0 ]; then
    echo "✗ Verification failed"
    exit 1
fi

# ============================================================================
# FINAL SUMMARY
# ============================================================================
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                 ✓ SETUP COMPLETE!                         ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Credentials configured:"
echo "  GCP Project:     $GCP_PROJECT"
echo "  Service Account: $SERVICE_ACCOUNT_FULL"
echo "  Key File:        $KEY_FILE"
echo "  .env File:       $ADK_DIR/.env"
echo ""
echo "Next steps:"
echo "  1. Test Gemini connection:"
echo "     cd $ADK_DIR"
echo "     python test_gemini.py"
echo ""
echo "  2. Run first scenario:"
echo "     python run_refund.py scenario-1-auto-approve"
echo ""
echo "  3. Check results:"
echo "     cat output/refund-demo-01/pipeline-output.json | jq '.'"
echo ""
