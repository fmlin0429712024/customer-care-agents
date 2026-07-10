# Quick Start — Run ADK Refund Agent Locally

**Yes, you can run the refund agent directly with Python — no server needed!**

## Setup (一次性)

```bash
cd adk_refund

# 1. Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -e .

# 3. Configure credentials
cp .env.example .env
# Edit .env with your GCP project and Gemini API key
nano .env

# 4. Verify setup
bash check_setup.sh
```

## Run Tests (直接 Python 调用)

### Option A: Quick Test (推荐 - 先做这个)

```bash
# 验证 Gemini 连接
python test_gemini.py
```

Expected output:
```
✓ google-genai imported
✓ google-adk imported
✓ Gemini client created
✓ gemini-2.5-pro is available
✓ ADK Agent created
✓ ALL TESTS PASSED
```

### Option B: Run Single Scenario

```bash
# Run scenario 1 (auto-approve)
python run_refund.py scenario-1-auto-approve
```

Output goes to:
```
output/refund-demo-01/pipeline-output.json
```

### Option C: Run All 7 Scenarios

```bash
# Run all scenarios
for scenario in scenario-1-auto-approve scenario-2-past-window scenario-3-in-transit \
                scenario-4-not-found scenario-5-high-value scenario-6-duplicate scenario-7-fraud-risk; do
  echo "Running $scenario..."
  python run_refund.py $scenario "batch-$(date +%s)"
done
```

## View Results

```bash
# Pretty print JSON output
cat output/refund-demo-01/pipeline-output.json | jq '.'

# Extract just the final customer response
cat output/refund-demo-01/pipeline-output.json | jq '.stages["customer-communication"]'

# List all output directories
ls -la output/
```

## Troubleshooting

### Issue: `ModuleNotFoundError: No module named 'google.adk'`

```bash
# Make sure venv is activated
source venv/bin/activate

# Reinstall
pip install google-adk>=1.31.0 google-genai>=1.0.0
```

### Issue: `GOOGLE_APPLICATION_CREDENTIALS` not found

```bash
# Check .env file
cat .env | grep GOOGLE_APPLICATION_CREDENTIALS

# If using service account key:
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/key.json

# Or set in .env:
echo "GOOGLE_APPLICATION_CREDENTIALS=/Users/fmlin/gcp-refund-agent-key.json" >> .env
```

### Issue: Gemini API error

```bash
# Verify credentials work
python test_gemini.py

# If it fails, check:
# 1. GENAI_API_KEY is set in .env
# 2. GCP project has Gemini API enabled:
#    gcloud services enable generativeaiapi.googleapis.com

# 3. Service account has proper IAM role
```

## How It Works (Architecture)

```
Python Script (run_refund.py)
    ↓
Creates SequentialAgent Pipeline
    ↓
Loads initial state (order_id, fraud_flags, reference data)
    ↓
Agent 1: order-lookup
  (calls Gemini to verify order + extract data)
    ↓
Agent 2: refund-decision
  (calls Gemini to apply policy rules)
    ↓
Agent 3: fraud-detection
  (calls Gemini to check for abuse patterns)
    ↓
Agent 4: customer-communication
  (calls Gemini to draft customer message)
    ↓
Saves output to JSON
    ↓
Python exits successfully
```

**Key point:** Each Agent makes ONE Gemini API call. Total time ~10-30 seconds per scenario.

## API Costs (Gemini 2.5 Pro)

- Input tokens: $0.075 per 1M tokens
- Output tokens: $0.30 per 1M tokens
- Each refund scenario: ~500-1000 tokens total
- Cost per scenario: ~$0.001-$0.003

Running all 7 scenarios: ~$0.01

## Environment Variables Reference

```bash
# Required
GOOGLE_CLOUD_PROJECT=linkhealth-care-2024
GENAI_API_KEY=your-api-key

# Optional (uses Application Default Credentials if not set)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

# Optional (default: gemini-2.5-pro)
ADK_MODEL=gemini-2.5-pro
```

## What Happens to Your Data?

✓ **Safe:** All order data stays local (in memory)  
✓ **Secure:** No data stored permanently  
✓ **Logged:** Only conversation with Gemini API is Gemini's standard logging  
✓ **Reversible:** All outputs are JSON files you control  

## Next Steps

1. ✅ Run `bash check_setup.sh` to verify environment
2. ✅ Run `python test_gemini.py` to test Gemini connection
3. ✅ Run `python run_refund.py scenario-1-auto-approve` to test pipeline
4. ✅ Check output: `cat output/refund-demo-01/pipeline-output.json | jq`
5. (Optional) Deploy to Cloud Run when ready

## One-Liner to Test Everything

```bash
bash check_setup.sh && python test_gemini.py && python run_refund.py scenario-1-auto-approve && echo "✓ SUCCESS"
```

---

**No server required.** Just Python + Gemini API = Refund Agent runs locally in ~30 seconds per scenario.
