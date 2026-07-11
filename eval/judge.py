"""Judge: the scoring heart of the eval loop.

Two axes, mirroring the two agent archetypes:

  - care   (coordinator) -> TRAJECTORY eval: did it route / slot-fill /
                             NOT self-decide?  (reference-free, behavioural)
  - refund (worker)      -> OUTCOME  eval: decision == golden? + does the
                             customer reply AGREE with that decision?  (LLM-judge)

Guiding rule:  PASS = the evaluator AGREES with what the agent did.
               FAIL = disagreement -> (future) human-in-the-loop.

The deterministic checks need zero external deps, so the whole loop runs
offline. The LLM-judge has a live Gemini path (--live-judge) and an offline
deterministic proxy so nothing is blocked on an API key.
"""

DECISIONS = {"APPROVE", "ESCALATE", "REJECT"}


def judge_care(case, trace):
    """Trajectory axis. Returns (result, checks)."""
    care = trace["care"]
    checks = {}
    # Did it delegate exactly when it should have?
    checks["delegate_when_expected"] = (
        care["delegated_to_refund"] == case["expected_delegate"]
    )
    if case["expected_delegate"]:
        # Slot-fill the right order id, and never make its own refund decision.
        checks["slot_fill_correct"] = (
            care.get("slot_filled_order_id") == case["order_id"]
        )
        checks["no_self_decision"] = (care.get("made_own_decision") is False)
    result = "PASS" if all(checks.values()) else "FAIL"
    return result, checks


def judge_refund(case, trace, use_llm=False):
    """Outcome axis. Only meaningful when the case should delegate."""
    if not case["expected_delegate"]:
        return "N/A", {}
    refund = trace.get("refund", {}) or {}
    checks = {}
    actual = refund.get("decision")
    # Crisp column: deterministic exact match against the policy golden answer.
    checks["decision_match"] = (actual == case["golden_decision"])
    # Fuzzy column: does the reply semantically AGREE with the decision?
    verdict, _reason = llm_judge_reply(refund.get("reply", ""), actual, case, use_llm=use_llm)
    checks["reply_agrees"] = (verdict == "AGREE")
    result = "PASS" if all(checks.values()) else "FAIL"
    return result, checks


# --- LLM-as-judge -----------------------------------------------------------

JUDGE_PROMPT = """You are an impartial QA evaluator for a customer-refund reply.

Decision the worker agent made: {decision}
Customer situation: {chat}
Agent's reply to the customer:
\"\"\"{reply}\"\"\"

Does the reply correctly and on-policy communicate that decision, with no
contradiction? Answer strictly as: AGREE or DISAGREE — then a one-line reason.
"""


def llm_judge_reply(reply, decision, case, use_llm=False):
    """Return (AGREE|DISAGREE, reason)."""
    if use_llm:
        return _live_gemini_judge(reply, decision, case)
    # Offline deterministic proxy for the LLM judge: keeps the loop runnable
    # with zero deps. The reply must be non-empty and must not contradict the
    # decision it is supposed to convey.
    reply_l = (reply or "").lower()
    if not reply_l.strip():
        return "DISAGREE", "empty reply"
    contradictions = {
        "APPROVE": ["cannot", "denied", "rejected", "unable to refund", "escalated"],
        "REJECT": ["approved", "refunded successfully", "on its way"],
        "ESCALATE": ["approved", "rejected", "unable to refund"],
    }
    for bad in contradictions.get(decision or "", []):
        if bad in reply_l:
            return "DISAGREE", f"reply says '{bad}' but decision was {decision}"
    return "AGREE", "reply consistent with decision"


def _live_gemini_judge(reply, decision, case):
    """Real LLM-as-judge via Gemini. Requires google-genai + auth."""
    from google import genai  # lazy import so offline runs need no dep

    client = genai.Client()
    prompt = JUDGE_PROMPT.format(decision=decision, chat=case["chat"], reply=reply)
    resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    text = (resp.text or "").strip()
    verdict = "AGREE" if text.upper().startswith("AGREE") else "DISAGREE"
    return verdict, text
