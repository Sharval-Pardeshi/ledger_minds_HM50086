# Person 1 - Prototype deliverable

Two things, per the Hour-1 kickoff and Prototype task table:

1. **The sample dataset** — `sample_data/bank_sample.csv` (40 rows, 2 months, one bank account, matching the `date, description, amount, type` format from the workflow doc).
2. **`process_csv()`** — reads that CSV, categorizes each row with keyword rules, and scores confidence. Output written to `sample_data/sample_clean.json`, which is the fixed "expected output" the rest of the team builds against from day 1.

## How to run it

```bash
python3 generate_dataset.py   # (re)generates bank_sample.csv — only needed if you want to change the data
python3 process_csv.py        # reads the CSV, writes sample_clean.json, prints a quick report
python3 test_process_csv.py   # runs the unit tests
```

## What's in the sample data (on purpose)

| Trap | Rows |
|---|---|
| Salary (income) | 1st of each month |
| Rent | 3rd of each month, via UPI, has a reference number |
| EMI | 5th of each month |
| Netflix (recurring subscription) | 6th of each month |
| A duplicate | `UPI/9988776655/RAKESH` appears twice, identical, May 16 — deliberately **not** deduped here, that's Hackathon Final task 6 |
| Ambiguous rows | `AMAZON.IN`, `UPI/AMAZON/GENERIC PURCHASE`, `UPI/FRIEND SPLIT DINNER/VIKAS`, `UPI/RANDOM MERCHANT XYZ` — these come out as **Likely** or **Uncertain**, not **Confirmed** |

Result on this data: **34 Confirmed, 2 Likely, 4 Uncertain** — a realistic mix, not everything clean.

## What each output field means

| Field | Computed here? | Notes |
|---|---|---|
| id, date, amount, direction, description, source | Yes | Source is always `"bank"` since this is a single-file CSV |
| category, confidence_score, confidence_label | **Yes — this is the actual prototype task** | Keyword rules in `process_csv.py`, top to bottom, first match wins |
| flow_type | Partial | Light heuristic only (income / card_bill_payment / real_expense). Full dedup + reconciliation is Hackathon Final task 6, not built yet |
| is_recurring, recurring_id | Stub | Always `false` / `null`. Real recurring-series detection is Hackathon Final task 8 |
| ref_id | Partial | Extracted from UPI references when present in the text, but nothing dedups on it yet |

## For P2 / P3 / P4

Build against `sample_data/sample_clean.json` — it's valid `CleanTransaction[]` per the Doc 01 contract. You don't need to wait for the real pipeline; swap it out at integration.

## Confidence bands used (team standard)

| Score | Label |
|---|---|
| ≥ 0.85 | Confirmed |
| 0.60 – 0.85 | Likely |
| < 0.60 | Uncertain |

## Next for Person 1 (not in this deliverable)

PDF parsing, LLM fallback, reconciliation, dedup/flow_type, recurring detection, the shared confidence-scorer library, masking — the 10-task Hackathon Final list.
