# Testing Cheat Sheet

Copy **one** prompt below, paste into a Claude Code chat. That's it.

> **Note:** These prompts rely on Claude recognizing the request and
> reaching for the `customer-refund` skill on its own — no file paths
> needed. If a prompt doesn't seem to trigger the skill, start a **fresh**
> Claude Code session in this project folder (a session opened before the
> skill files existed won't have it in its registry yet).

---

### 1. Auto-Approve ✅
```
A customer wants a refund for order 67890.
```
Expect: **APPROVE** — AUTO_APPROVED — $49.00

---

### 2. Escalate: Past Refund Window 👤
```
A customer wants a refund for order 12345.
```
Expect: **ESCALATE** — PAST_REFUND_WINDOW — priority NORMAL

---

### 3. Escalate: Still In Transit 👤
```
A customer wants a refund for order 11111.
```
Expect: **ESCALATE** — IN_TRANSIT — priority HIGH

---

### 4. Reject: Order Not Found ❌
```
A customer wants a refund for order 99999.
```
Expect: **REJECT** — ORDER_NOT_FOUND

---

### 5. Escalate: High-Value Order 👤
```
A customer wants a refund for a $750 order that was delivered 2 days ago.
```
Expect: **ESCALATE** — HIGH_VALUE_ORDER — priority HIGH

---

### 6. Escalate: Duplicate Refund Detected 👤
```
A customer wants a refund for order 67890 ($49, delivered 2 days ago), but
this order already has an open refund ticket from last week.
```
Expect: **ESCALATE** — DUPLICATE_REFUND — priority HIGH

---

### 7. Escalate: Refund Frequency Abuse 👤
```
A customer wants a refund for order 67890 ($49, delivered 2 days ago), but
this customer has already requested 4 refunds in the past 30 days.
```
Expect: **ESCALATE** — FRAUD_RISK — priority HIGH

---

### Run All 7 at Once (regression pass)
```
Run through all the refund test scenarios you have reference data for, and
tell me whether each outcome matches what's expected. Summarize pass/fail.
```

---

## Legend

✅ Auto-resolved &nbsp; 👤 Escalated to human &nbsp; ❌ Rejected

## If a Prompt Doesn't Trigger the Skill

1. Make sure you're in a **new** Claude Code session started after the
   skill files were created.
2. If it still doesn't trigger, you can fall back to naming the skill
   directly: "Use the customer-refund skill to process this." — a small
   nudge, still no path required.

## Adding a New Test Case

1. Add the order to the skill's reference data.
2. Add the expected outcome alongside it.
3. Add a row here.
