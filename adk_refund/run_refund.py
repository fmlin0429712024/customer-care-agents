#!/usr/bin/env python3
"""
Customer Refund Pipeline — ADK Implementation (Self-Contained)

Usage:
  python run_refund.py <scenario_name> [run_name]

Examples:
  python run_refund.py scenario-1-auto-approve
  python run_refund.py scenario-2-past-window refund-run-02
"""
import asyncio
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from refund_agent.agent import build_pipeline
from refund_agent.tools import (
    list_scenarios,
    load_scenario_details,
    get_orders_reference_json,
)

DIVIDER = "=" * 70
DATA_DIR = Path(__file__).parent / "data"


async def run(scenario: str, run_name: str) -> None:
    """Run the refund pipeline for a given scenario."""

    # Load scenario data
    scenario_data = load_scenario_details(scenario)
    order_id = scenario_data.get("order_id", "67890")
    fraud_flags = scenario_data.get("fraud_flags", "")

    # Load reference data
    orders_json = get_orders_reference_json()

    # Build pipeline
    pipeline = build_pipeline(run_name=run_name)
    session_service = InMemorySessionService()
    runner = Runner(
        agent=pipeline,
        session_service=session_service,
        app_name="refund_pipeline",
    )

    # Create session with initial state
    session = await session_service.create_session(
        app_name="refund_pipeline",
        user_id="demo",
        state={
            "run_name": run_name,
            "scenario": scenario,
            "order_id": order_id,
            "fraud_flags": fraud_flags,
            "reference_orders": orders_json,
        },
    )

    print(f"\n{DIVIDER}")
    print("CUSTOMER REFUND PIPELINE — ADK IMPLEMENTATION")
    print(f"{DIVIDER}")
    print(f"Scenario    : {scenario}")
    print(f"Run name    : {run_name}")
    print(f"Order ID    : {order_id}")
    if fraud_flags:
        print(f"Fraud flags : {fraud_flags}")
    print(f"Expected    : {scenario_data.get('expected_decision', '?')} — {scenario_data.get('expected_reason', '?')}")
    print(f"{DIVIDER}\n")

    # Initialize output accumulator
    full_output = {
        "scenario": scenario,
        "run_name": run_name,
        "order_id": order_id,
        "expected_decision": scenario_data.get("expected_decision"),
        "expected_reason": scenario_data.get("expected_reason"),
        "stages": {},
    }

    # Run the pipeline
    message = genai_types.Content(
        role="user",
        parts=[genai_types.Part(
            text=f"Process refund scenario '{scenario}' for order {order_id}. "
                 f"Apply the full refund pipeline: order lookup → decision → fraud detection → customer communication."
        )],
    )

    current_stage = None
    stage_buffer = []

    async for event in runner.run_async(
        user_id="demo",
        session_id=session.id,
        new_message=message,
    ):
        # Capture text output
        if event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    text = part.text

                    # Detect stage transitions
                    if "ORDER LOOKUP RESULT" in text:
                        current_stage = "order-lookup"
                        stage_buffer = []
                    elif "REFUND DECISION" in text:
                        if current_stage:
                            full_output["stages"][current_stage] = "\n".join(stage_buffer)
                        current_stage = "refund-decision"
                        stage_buffer = []
                    elif "FRAUD SCREEN RESULT" in text:
                        if current_stage:
                            full_output["stages"][current_stage] = "\n".join(stage_buffer)
                        current_stage = "fraud-detection"
                        stage_buffer = []
                    elif "CUSTOMER RESPONSE" in text:
                        if current_stage:
                            full_output["stages"][current_stage] = "\n".join(stage_buffer)
                        current_stage = "customer-communication"
                        stage_buffer = []

                    if current_stage:
                        stage_buffer.append(text)

                    print(text)

        # Capture tool calls
        if hasattr(event, "tool_call") and event.tool_call:
            print(f"\n[🔧 Tool] {event.tool_call.name}\n")

    # Save final stage
    if current_stage and stage_buffer:
        full_output["stages"][current_stage] = "\n".join(stage_buffer)

    # Save outputs
    output_dir = Path(__file__).parent / "output" / run_name
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save full pipeline output
    full_output_file = output_dir / "pipeline-output.json"
    full_output_file.write_text(json.dumps(full_output, indent=2))

    # Extract final decision from output
    final_decision = "?"
    final_reason = "?"
    for stage, content in full_output["stages"].items():
        if "DECISION" in stage.upper():
            if "APPROVE" in content and "ESCALATE" not in content:
                final_decision = "APPROVE"
            elif "ESCALATE" in content:
                final_decision = "ESCALATE"
            elif "REJECT" in content:
                final_decision = "REJECT"
            # Extract reason codes
            for line in content.split("\n"):
                if "reason" in line.lower() or "code" in line.lower():
                    final_reason = line.strip()

    print(f"\n{DIVIDER}")
    print(f"✓ Pipeline complete")
    print(f"✓ Expected: {scenario_data.get('expected_decision')} — {scenario_data.get('expected_reason')}")
    print(f"✓ Got:      {final_decision} — {final_reason}")
    print(f"✓ Output saved to: {full_output_file}")
    print(f"{DIVIDER}\n")


if __name__ == "__main__":
    scenario = sys.argv[1] if len(sys.argv) > 1 else "scenario-1-auto-approve"
    run_name = sys.argv[2] if len(sys.argv) > 2 else "refund-demo-01"

    # Verify scenario exists
    if not (DATA_DIR / scenario).exists():
        print(f"❌ Scenario '{scenario}' not found.")
        print(f"\nAvailable scenarios:")
        for s in sorted(DATA_DIR.glob("scenario-*")):
            print(f"  - {s.name}")
        sys.exit(1)

    asyncio.run(run(scenario, run_name))
