#!/usr/bin/env python3
"""
Quick test to verify Gemini 2.5 Pro connection.

Usage:
  python test_gemini.py
"""
import os
from dotenv import load_dotenv

load_dotenv()

print("=" * 60)
print("GEMINI CONNECTION TEST")
print("=" * 60)

# Test 1: Check environment
print("\n[1] Environment Setup")
gcp_project = os.getenv("GOOGLE_CLOUD_PROJECT")
genai_key = os.getenv("GENAI_API_KEY")
credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

print(f"  GCP Project: {gcp_project or '❌ NOT SET'}")
print(f"  GENAI API Key: {'✓ SET' if genai_key else '❌ NOT SET'}")
print(f"  Credentials Path: {credentials_path or '❌ NOT SET'}")

if not (gcp_project or genai_key):
    print("\n❌ Missing credentials. Run this first:")
    print("   cp .env.example .env")
    print("   nano .env  # Add your GCP credentials")
    exit(1)

# Test 2: Import libraries
print("\n[2] Library Imports")
try:
    from google import genai
    print("  ✓ google-genai imported")
except ImportError as e:
    print(f"  ❌ Failed to import google-genai: {e}")
    print("   Install with: pip install google-genai")
    exit(1)

try:
    from google.adk.agents import Agent
    print("  ✓ google-adk imported")
except ImportError as e:
    print(f"  ❌ Failed to import google-adk: {e}")
    print("   Install with: pip install google-adk")
    exit(1)

# Test 3: Create Gemini client
print("\n[3] Gemini Client Connection")
try:
    client = genai.Client(api_key=genai_key)
    print("  ✓ Gemini client created")
except Exception as e:
    print(f"  ❌ Failed to create Gemini client: {e}")
    exit(1)

# Test 4: Test model availability
print("\n[4] Model Availability")
try:
    model = "gemini-2.5-pro"
    # Try a simple completion
    response = client.models.generate_content(
        model=model,
        contents="Say 'Refund Agent Ready' in exactly 3 words."
    )
    print(f"  ✓ {model} is available")
    print(f"  ✓ Response: {response.text[:100]}")
except Exception as e:
    print(f"  ❌ Model test failed: {e}")
    exit(1)

# Test 5: Test ADK Agent
print("\n[5] ADK Agent Creation")
try:
    from refund_agent.agent import _build_order_lookup_agent
    agent = _build_order_lookup_agent()
    print(f"  ✓ ADK Agent created: {agent.name}")
    print(f"  ✓ Model: {agent.model}")
except Exception as e:
    print(f"  ❌ Failed to create ADK agent: {e}")
    exit(1)

print("\n" + "=" * 60)
print("✓ ALL TESTS PASSED")
print("=" * 60)
print("\nYou can now run:")
print("  python run_refund.py scenario-1-auto-approve")
print()
