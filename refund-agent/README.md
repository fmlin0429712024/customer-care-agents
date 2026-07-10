# AI-Powered Customer Refund Agent — PoC

A rapid AI prototype demonstrating how Claude + Claude Skills can automate refund processing for e-commerce customer service.

| Time | Section | Focus |
|------|---------|-------|
| 0–2 min | §1 Problem | Business context & metrics |
| 2–5 min | §2 AI Opportunities | Five refund pipeline stages |
| 5–10 min | §4 Prototype | Live Cowork demo |
| 10–12 min | §3 Quality & Compliance | Fraud & dispute handling |
| 12–15 min | §5 Extensibility | Strategic vision |

---

## 1. Problem

A typical e-commerce support team manually reviews 1,000–5,000 refund requests per day. Decisions require checking order status, eligibility rules, delivery timeline, and fraud signals — creating a 2–4 hour average response time, 15–20% of requests escalated unnecessarily, and high manual workload on peak days.

| Metric | Current | Goal |
|--------|---------|------|
| Average response time | 2–4 hours | **< 15 min** (auto-approved) |
| Manual escalation rate | 15–20% | **< 5%** (only genuine edge cases) |
| Auto-approval rate | 0% | **60–70%** |
| Customer satisfaction (refunds) | ~70% | **> 90%** |

---

## 2. Five AI Opportunities

### 1. Order Lookup — Query & Verify ← *Prototype built*
Order data arrives via order ID. AI verifies order exists, extracts status (delivered / in-transit), amount, and delivery date — foundational for all downstream decisions.

### 2. Refund Policy Engine ← *Prototype built*
Eligibility rules are deterministic: 5-day delivery window, $500 auto-approval cap, delivery status check. AI reads the policy rulebook, never invents exceptions — eliminating inconsistent decisions.

### 3. Refund Decision — Apply Rules ← *Prototype built*
Given order data and policy, AI produces a single deterministic decision: APPROVE / ESCALATE / REJECT with a reason code (PAST_WINDOW, HIGH_VALUE, IN_TRANSIT, etc.) and priority level.

### 4. Fraud Detection — Abuse Screening ← *Prototype built*
Before auto-approving, AI screens for duplicate refunds on the same order and refund frequency abuse (>3 in 30 days). Catches patterns; escalates suspicious activity to the fraud team.

### 5. Customer Communication — Dialogue Automation ← *Prototype built*
Same decision + same policy rules, but customer-facing tone varies. AI crafts APPROVE messages (celebratory, timeline clear), ESCALATE messages (empathetic, ticket provided), and REJECT messages (helpful guidance).

### How the Five Stages Connect

```
Order ID
   ↓
[1] Order Lookup       — verify & extract order data
   ↓
[2] Refund Policy      — eligibility rules (reference)
   ↓
[3] Refund Decision    — apply rules → APPROVE / ESCALATE / REJECT
   ↓
[4] Fraud Detection    — screen tentative approvals for abuse
   ↓
[5] Customer Communication — craft the response
```

---

## 3. Refund Quality & Compliance

*Directly addressing: "How can AI improve refund speed while preventing abuse and maintaining fairness?"*

Each AI step has a different risk profile. The design principle: push toward deterministic outputs wherever possible; escalate to human judgment where not.

| Stage | Risk | Why | Mitigation |
|-------|------|-----|------------|
| 1. Lookup | 🟢 Low | Data retrieval only — no judgment | Query a trusted order database; never fabricate data |
| 2. Policy | 🟢 Low | Rules are written, static, and version-controlled | Policy file is a source of truth; changes are audited |
| 3. Decision | 🟡 Medium | Rule application is deterministic but edge cases exist | Clear decision tree with explicit reason codes for every path |
| 4. Fraud | 🟡 Medium | Patterns may have false positives (e.g., legitimate high-frequency shopper) | Escalate to human on ambiguous flags; maintain non-accusatory tone |
| 5. Communication | 🟢 Low | Tone only — never invents policy | Template-based + decision context; human reviews escalation messages |

---

## 4. Prototype — Claude Refund Pipeline

End-to-end pipeline implemented as a **Claude Cowork Skills plugin** (runs in Claude desktop or web — no local setup required).

### Pipeline Stages

```
Customer refund request
        ↓
[1] Order Lookup        — verify order exists, extract data
        ↓
[2] Refund Policy       — check eligibility rules
        ↓
[3] Refund Decision     — apply rules → APPROVE / ESCALATE / REJECT
        ↓
[4] Fraud Detection     — screen for duplicate / frequency abuse
        ↓
[5] Customer Communication — craft the response
```

### Demo Scenarios (7 cases)

| # | Order | Amount | Status | Days | Expected Decision | Reason Code |
|---|-------|--------|--------|------|-------------------|-------------|
| 1 ✅ | 67890 | $49 | delivered | 2 | APPROVE | AUTO_APPROVED |
| 2 👤 | 12345 | $99 | delivered | 7 | ESCALATE | PAST_REFUND_WINDOW |
| 3 👤 | 11111 | $29 | in_transit | — | ESCALATE | IN_TRANSIT |
| 4 ❌ | 99999 | — | not found | — | REJECT | ORDER_NOT_FOUND |
| 5 👤 | HIGH001 | $750 | delivered | 2 | ESCALATE | HIGH_VALUE_ORDER |
| 6 👤 | 67890 | $49 | delivered | 2 | ESCALATE | DUPLICATE_REFUND |
| 7 👤 | 67890 | $49 | delivered | 2 | ESCALATE | FRAUD_RISK |

Legend: ✅ Auto-resolved · 👤 Escalated to human · ❌ Rejected

### Run the Demo

**Claude Cowork (recommended):** Open this project in Claude desktop or claude.ai → paste any prompt from [`TESTING.md`](./TESTING.md)

Example:
```
A customer wants a refund for order 67890.
```

**All 7 scenarios at once:**
```
Run all 7 test scenarios and report pass/fail.
```

---

## 5. Extensibility

### ① Multi-Channel Refund Requests
Current: order ID only. Future: support refund-by-email, SMS, social media DM, or chat. AI routes to the same pipeline, normalizes the input (extract order ID from context clues), and produces a response in the same channel.
- Status: designed, not yet implemented

### ② International Expansion & Multi-Currency
Refund rules differ by region (EU = 14-day window, US = varies by state/retailer). Policy rules become region-aware; fraud thresholds adjust for local purchasing patterns.
- Status: designed, not yet tested with regional data

### ③ Complex Refund Scenarios
Current: simple refund / no-refund. Future: partial refunds (damaged goods), store credit alternatives, exchange-first-then-refund workflows. New reason codes + escalation routing for each scenario.
- Status: planned

### ④ Reverse Integration with Ticketing Systems
Current: escalation tickets logged in-memory. Future: direct write to Jira / Linear / Zendesk with auto-assignment, SLA timers, and automated status updates back to the customer.
- Status: designed, not yet connected

### ⑤ Eval Loop with Human-in-the-Loop
```
Customer Refund Decisions (AI)
   ↓
Grade against expected outcomes (Eval Agent)
   ↓ Match? → Validated
   ↓
Mismatch? → Escalate to human for audit
```

In production, real refund decisions feed into metrics dashboards. Repeated mismatches signal a policy rule that needs updating or an abuse pattern that needs a new fraud check.
- Status: designed, not yet connected to metrics

### ⑥ Refund Policy Versioning & A/B Testing
Policy rules live as versioned markdown files. Teams can propose policy changes, A/B test the new rule on historical cases, and measure impact before rolling out.
- Status: designed, not yet tested

---

## 6. Tech Stack

| Layer | Prototype | Production Path |
|-------|-----------|-----------------|
| AI Model | Claude Haiku / Sonnet (Anthropic API) | Claude Opus (Anthropic API) or Gemini Pro (Google Vertex) |
| Orchestration | Claude Code CLI (Skills Plugin) | Google ADK SequentialAgent or Anthropic Agents SDK |
| Business Rules | Plain-English markdown skills | Markdown skills → internal wiki + versioning |
| State | In-memory JSON (prototype) | PostgreSQL / Firebase |
| Auth | Local credentials | OAuth2 + company SSO |
| Compliance | — | SOC 2, GDPR (if EU customers), PCI DSS (payment data) |

---

## Project Structure

```
.
├── README.md                                     # This file
├── CLAUDE.md                                     # Project overview + flow diagrams
├── TESTING.md                                    # Test prompts (copy-paste ready)
└── .claude/skills/customer-refund/               # Orchestrator skill
    ├── SKILL.md                                   # Pipeline overview
    ├── order-lookup/SKILL.md                      # Stage 1
    ├── refund-policy/SKILL.md                     # Stage 2
    ├── refund-decision/SKILL.md                   # Stage 3
    ├── fraud-detection/SKILL.md                   # Stage 4
    ├── customer-communication/SKILL.md            # Stage 5
    ├── escalation-rules/SKILL.md                  # Escalation triggers
    ├── escalation-workflow/SKILL.md               # Ticket creation + SLA
    └── reference/
        ├── orders.json                            # Test order data
        └── test-scenarios.json                    # Expected outcomes
```

---

## Next Steps

1. **Test in Claude Cowork** — Run the 7 scenarios in `TESTING.md`
2. **Connect to real data** — Replace `reference/orders.json` with a live order database
3. **Implement payment refund API** — Wire up actual refund processing (Stripe, PayPal, etc.)
4. **Integrate ticketing** — Connect escalation-workflow to Jira / Linear
5. **Deploy metrics & monitoring** — Feed decisions into analytics; build the Eval Loop

---

**Status:** PoC — Skills Architecture v1.0  
**Created:** 2026-07-09  
**Repository:** https://github.com/fmlin0429712024/customer-refund-agent
