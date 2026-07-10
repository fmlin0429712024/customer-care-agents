#!/bin/bash
# Setup verification script for ADK Refund Agent

set -e

echo "=========================================="
echo "ADK REFUND AGENT — SETUP VERIFICATION"
echo "=========================================="

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check 1: Python version
echo -e "\n[1] Python Version"
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
REQUIRED_VERSION="3.11"
if [[ "$PYTHON_VERSION" > "$REQUIRED_VERSION" ]] || [[ "$PYTHON_VERSION" == "$REQUIRED_VERSION" ]]; then
    echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION (required: >=3.11)"
else
    echo -e "${RED}✗${NC} Python $PYTHON_VERSION (required: >=3.11)"
    exit 1
fi

# Check 2: Virtual environment
echo -e "\n[2] Virtual Environment"
if [[ -n "$VIRTUAL_ENV" ]]; then
    echo -e "${GREEN}✓${NC} venv activated: $VIRTUAL_ENV"
else
    echo -e "${YELLOW}⚠${NC} No venv detected. Run: source venv/bin/activate"
    exit 1
fi

# Check 3: Required packages
echo -e "\n[3] Required Packages"
packages=("google-adk" "google-genai" "python-dotenv")
for package in "${packages[@]}"; do
    if python3 -c "import ${package//-/_}" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} $package"
    else
        echo -e "${RED}✗${NC} $package — install with: pip install $package"
        exit 1
    fi
done

# Check 4: .env file
echo -e "\n[4] Environment Configuration"
if [[ -f ".env" ]]; then
    echo -e "${GREEN}✓${NC} .env file exists"

    # Check .env values
    if grep -q "GOOGLE_CLOUD_PROJECT=" .env; then
        PROJECT=$(grep "GOOGLE_CLOUD_PROJECT=" .env | cut -d= -f2)
        echo -e "  ${GREEN}✓${NC} GCP Project: $PROJECT"
    else
        echo -e "  ${RED}✗${NC} GOOGLE_CLOUD_PROJECT not set in .env"
    fi

    if grep -q "GENAI_API_KEY=" .env && ! grep -q "GENAI_API_KEY=your-api-key" .env; then
        echo -e "  ${GREEN}✓${NC} GENAI_API_KEY is set"
    else
        echo -e "  ${RED}✗${NC} GENAI_API_KEY not configured in .env"
    fi

    if grep -q "GOOGLE_APPLICATION_CREDENTIALS=" .env; then
        CREDS=$(grep "GOOGLE_APPLICATION_CREDENTIALS=" .env | cut -d= -f2)
        if [[ -f "$CREDS" ]]; then
            echo -e "  ${GREEN}✓${NC} Credentials file found: $CREDS"
        else
            echo -e "  ${YELLOW}⚠${NC} Credentials file not found: $CREDS"
        fi
    else
        echo -e "  ${YELLOW}⚠${NC} GOOGLE_APPLICATION_CREDENTIALS not set (using Application Default)"
    fi
else
    echo -e "${YELLOW}⚠${NC} .env not found. Create with:"
    echo "   cp .env.example .env"
    echo "   nano .env"
    exit 1
fi

# Check 5: GCP credentials
echo -e "\n[5] GCP Authentication"
if [[ -n "$GOOGLE_APPLICATION_CREDENTIALS" ]] && [[ -f "$GOOGLE_APPLICATION_CREDENTIALS" ]]; then
    echo -e "  ${GREEN}✓${NC} Service account key: $GOOGLE_APPLICATION_CREDENTIALS"
elif command -v gcloud &> /dev/null; then
    GCLOUD_ACCOUNT=$(gcloud config get-value account 2>/dev/null || echo "not set")
    echo -e "  ${GREEN}✓${NC} gcloud account: $GCLOUD_ACCOUNT"
else
    echo -e "  ${YELLOW}⚠${NC} No GCP credentials configured"
fi

# Check 6: Test data
echo -e "\n[6] Test Data"
if [[ -d "data/scenario-1-auto-approve" ]]; then
    SCENARIO_COUNT=$(ls -d data/scenario-* 2>/dev/null | wc -l)
    echo -e "${GREEN}✓${NC} Found $SCENARIO_COUNT test scenarios"
else
    echo -e "${RED}✗${NC} Test scenarios not found"
    exit 1
fi

# Check 7: Python imports
echo -e "\n[7] Python Imports"
python3 -c "from refund_agent.agent import build_pipeline; print('${GREEN}✓${NC} refund_agent imports OK')" || {
    echo -e "${RED}✗${NC} Failed to import refund_agent"
    exit 1
}

# Check 8: Git safety
echo -e "\n[8] Git Safety (.gitignore)"
if grep -q ".env" .gitignore 2>/dev/null && grep -q "*-key.json" .gitignore 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Sensitive files are gitignored"
else
    echo -e "${YELLOW}⚠${NC} Check .gitignore — ensure .env and *-key.json are listed"
fi

echo -e "\n=========================================="
echo -e "${GREEN}✓ SETUP VERIFICATION COMPLETE${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Run test_gemini.py to verify Gemini connection:"
echo "     python test_gemini.py"
echo ""
echo "  2. Run a test scenario:"
echo "     python run_refund.py scenario-1-auto-approve"
echo ""
echo "  3. Check output:"
echo "     cat output/refund-demo-01/pipeline-output.json | jq '.'"
echo ""
