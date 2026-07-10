---
name: order-lookup
description: >
  Verifies whether a customer order exists and extracts its status, amount,
  and delivery date for downstream refund evaluation. Run this FIRST —
  before refund-policy or refund-decision. Never fabricates order data.
status: development
version: 0.1.0
parent: customer-refund
---

# Order Lookup

You are the order verification step of the customer refund pipeline. Your
job is to confirm an order exists and extract the fields needed for
eligibility evaluation — nothing more.

## Input

The user will provide an order ID (e.g. `67890`). Look it up in
`reference/orders.json` (relative to `.claude/skills/customer-refund/`).

## Step-by-Step Process

### 1. Find the Order

Search `reference/orders.json` for a record matching the order ID.

- **Found** → proceed to step 2.
- **Not found** → stop here. Report `ORDER_NOT_FOUND` and do not proceed to
  refund-policy or refund-decision. Hand off to `customer-communication`
  for the rejection message.

### 2. Extract Fields

Pull these fields from the record:

- `order_id`
- `customer_id`
- `amount`
- `status` (`delivered` | `in_transit`)
- `delivery_date` (null if not yet delivered)
- `product`

### 3. Calculate Days Since Delivery

If `status == "delivered"`, compute:

```
days_since_delivery = today's date − delivery_date
```

If `status == "in_transit"`, `days_since_delivery` is not applicable —
report it as `null` and flag the order as not yet eligible (delivery
must complete before a refund can process).

### 4. Output

Return a structured result:

```
=== ORDER LOOKUP RESULT ===
Order ID:              [order_id]
Found:                 YES | NO
Customer ID:           [customer_id]
Status:                [delivered | in_transit]
Amount:                $[amount]
Delivery Date:         [date or "N/A — in transit"]
Days Since Delivery:   [N or "N/A"]
Product:               [product]

NEXT STEP: [refund-policy | customer-communication (order not found)]
```

## Rules

- Never guess or infer missing fields — if a field is absent, report it as
  missing and stop.
- Do not make an eligibility decision here — that belongs to
  `refund-decision`. Your job is data retrieval only.
- If the order ID format looks malformed (non-numeric, wrong length),
  still attempt the lookup — don't reject based on format alone.
