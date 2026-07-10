#!/bin/bash
# GCP Authentication Setup — Copy & Paste Commands
# This script automates all GCP setup steps

set -e

GCP_PROJECT="linkhealth-care-2024"
SERVICE_ACCOUNT="refund-agent-dev"
KEY_FILE="$HOME/gcp-refund-agent-key.json"

echo "=========================================="
echo "GCP AUTHENTICATION SETUP"
echo "=========================================="
echo "Project: $GCP_PROJECT"
echo "Service Account: $SERVICE_ACCOUNT"
echo "Key File: $KEY_FILE"
echo "=========================================="

# Step 1: Install gcloud CLI
echo -e "\n[Step 1] Installing Google Cloud CLI..."
if ! command -v gcloud &> /dev/null; then
    echo "Installing gcloud CLI..."
    curl https://sdk.cloud.google.com | bash
    exec -l $SHELL
else
    echo "✓ gcloud CLI already installed"
    gcloud --version
fi

# Step 2: Set default project
echo -e "\n[Step 2] Setting default GCP project..."
gcloud config set project $GCP_PROJECT
gcloud config list | grep "project ="

# Step 3: Enable APIs
echo -e "\n[Step 3] Enabling required APIs..."
gcloud services enable generativeaiapi.googleapis.com
gcloud services enable aiplatform.googleapis.com
gcloud services enable cloudruntime.googleapis.com
echo "✓ APIs enabled"

# Step 4: Create service account
echo -e "\n[Step 4] Creating service account..."
if gcloud iam service-accounts describe $SERVICE_ACCOUNT@$GCP_PROJECT.iam.gserviceaccount.com &>/dev/null; then
    echo "✓ Service account already exists"
else
    gcloud iam service-accounts create $SERVICE_ACCOUNT \
        --display-name="Refund Agent — Local Development"
    echo "✓ Service account created"
fi

# Step 5: Grant IAM roles
echo -e "\n[Step 5] Granting IAM permissions..."
gcloud projects add-iam-policy-binding $GCP_PROJECT \
    --member=serviceAccount:$SERVICE_ACCOUNT@$GCP_PROJECT.iam.gserviceaccount.com \
    --role=roles/aiplatform.user \
    --quiet
echo "✓ IAM role granted"

# Step 6: Create service account key
echo -e "\n[Step 6] Creating service account key..."
if [[ -f "$KEY_FILE" ]]; then
    echo "⚠ Key file already exists: $KEY_FILE"
    read -p "Overwrite? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping key creation"
    else
        gcloud iam service-accounts keys create $KEY_FILE \
            --iam-account=$SERVICE_ACCOUNT@$GCP_PROJECT.iam.gserviceaccount.com
        chmod 600 $KEY_FILE
        echo "✓ Key created: $KEY_FILE"
    fi
else
    gcloud iam service-accounts keys create $KEY_FILE \
        --iam-account=$SERVICE_ACCOUNT@$GCP_PROJECT.iam.gserviceaccount.com
    chmod 600 $KEY_FILE
    echo "✓ Key created: $KEY_FILE"
fi

# Step 7: Create .env file
echo -e "\n[Step 7] Creating .env configuration..."
if [[ ! -f ".env" ]]; then
    cp .env.example .env
    echo "✓ .env file created from template"
fi

# Update .env with actual credentials
sed -i '' "s|GOOGLE_APPLICATION_CREDENTIALS=.*|GOOGLE_APPLICATION_CREDENTIALS=$KEY_FILE|" .env
sed -i '' "s|GOOGLE_CLOUD_PROJECT=.*|GOOGLE_CLOUD_PROJECT=$GCP_PROJECT|" .env
echo "✓ .env updated with GCP credentials"

# Step 8: Verify authentication
echo -e "\n[Step 8] Verifying authentication..."
export GOOGLE_APPLICATION_CREDENTIALS=$KEY_FILE

python3 -c "
try:
    from google.auth import default
    creds, project = default()
    print(f'✓ Authenticated with service account')
    print(f'✓ Project: {project}')
    print(f'✓ Service Account: {creds.service_account_email}')
except Exception as e:
    print(f'✗ Authentication failed: {e}')
    exit(1)
"

# Step 9: Setup verification
echo -e "\n[Step 9] Running full setup check..."
bash check_setup.sh

echo -e "\n=========================================="
echo "✓ GCP AUTHENTICATION COMPLETE"
echo "=========================================="
echo -e "\nNext: Test Gemini connection"
echo "  cd adk_refund"
echo "  python test_gemini.py"
echo -e "\nThen: Run first scenario"
echo "  python run_refund.py scenario-1-auto-approve"
echo ""
