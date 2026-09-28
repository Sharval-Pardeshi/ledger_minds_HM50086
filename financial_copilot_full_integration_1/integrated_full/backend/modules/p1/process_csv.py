"""
PERSON 1 - PROTOTYPE DELIVERABLE

    process_csv(file_path) -> list[CleanTransaction]

Reads a bank-statement-style CSV (date, description, amount, type) and returns
a list of transactions matching the team's CleanTransaction contract (Doc 01,
section 1), with categorization and a confidence score computed by keyword
rules.

FIELDS THIS FUNCTION ACTUALLY COMPUTES (prototype scope):
    id, date, amount, direction, description, source, category,
    confidence_score, confidence_label

FIELDS STUBBED FOR NOW (built in later Hackathon Final tasks, not prototype):
    flow_type       -> light heuristic only here (income / card_bill_payment /
                        real_expense); full dedup + reconciliation logic is
                        task 6 of the Hackathon Final build.
    is_recurring,
    recurring_id    -> always False / null here; real recurring-series
                        detection is task 8 of the Hackathon Final build.
    ref_id          -> extracted opportunistically from UPI references so the
                        field exists, but nothing dedups on it yet (task 6).

Run this file directly to process sample_data/bank_sample.csv and write
sample_data/sample_clean.json — the fixed "expected output" your teammates
build against from day 1.
"""
import csv
import json
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Confidence bands — shared with the whole team (Doc 01, section 1)
# ---------------------------------------------------------------------------
def confidence_label(score: float) -> str:
    if score >= 0.85:
        return "Confirmed"
    if score >= 0.60:
        return "Likely"
    return "Uncertain"


# ---------------------------------------------------------------------------
# Keyword rules
# Each entry: (keywords, category, confidence)
# Checked top to bottom; first match wins. Keep specific/high-confidence
# merchant matches near the top, generic/ambiguous ones near the bottom.
# ---------------------------------------------------------------------------
RULES = [
    # --- Income ---
    (["salary credit", "salary"], "Income", 0.97),

    # --- Rent ---
    (["rent"], "Rent", 0.93),

    # --- Loan / EMI ---
    (["emi", "loan"], "Loan/EMI", 0.95),

    # --- Investments ---
    (["sip", "mutual fund", "index fund"], "Investments", 0.95),

    # --- Subscriptions (clean merchant names -> high confidence) ---
    (["netflix", "spotify", "prime video", "hotstar"], "Subscriptions", 0.96),

    # --- Food delivery ---
    (["swiggy", "zomato"], "Food", 0.94),

    # --- Groceries ---
    (["bigbasket", "dmart", "grocery"], "Groceries", 0.93),

    # --- Transport ---
    (["ola", "uber", "petrol", "hpcl", "iocl", "fuel"], "Transport", 0.92),

    # --- Utilities ---
    (["electricity", "bses", "airtel", "jio", "wifi", "broadband"], "Utilities", 0.90),

    # --- Healthcare ---
    (["pharmacy", "apollo", "hospital", "clinic"], "Healthcare", 0.90),

    # --- Card bill (flow_type hint, category still useful for display) ---
    (["credit card bill"], "Card Payment", 0.95),

    # --- Cash ---
    (["atm withdrawal"], "Cash Withdrawal", 0.90),

    # --- Shopping: two tiers on purpose ---
    # Named marketplace with no further context -> ambiguous, so LOWER
    # confidence even though the merchant is known (Amazon sells everything
    # from groceries to electronics -- this is intentional, see team notes
    # on ambiguous transactions).
    (["flipkart", "myntra"], "Shopping", 0.91),
    (["amazon"], "Shopping", 0.70),  # deliberately "Likely", not "Confirmed"

    # --- Generic personal UPI transfer: no merchant, no category signal ---
    (["friend split", "/rakesh", "/vikas"], "Uncategorized", 0.35),
]

# Extracts a UPI reference number if present, e.g. "UPI/408213445/..."
_REF_PATTERN = re.compile(r"UPI/(\d+)/")

# Rough flow_type heuristic -- NOT the real dedup/reconciliation logic
# (that's Hackathon Final task 6). Just enough so the field isn't empty.
def guess_flow_type(description: str, direction: str) -> str:
    desc = description.lower()
    if direction == "credit":
        return "income"
    if "credit card bill" in desc:
        return "card_bill_payment"
    return "real_expense"


def categorize(description: str):
    """Returns (category, confidence_score) for a transaction description."""
    desc_lower = description.lower()
    for keywords, category, score in RULES:
        if any(k in desc_lower for k in keywords):
            return category, score
    # No rule matched at all
    return "Uncategorized", 0.30


def process_csv(file_path: str) -> list:
    """
    Reads a CSV with columns: date, description, amount, type
    Returns a list of dicts matching the CleanTransaction contract.
    """
    transactions = []
    with open(file_path, newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=1):
            description = row["description"].strip()
            amount = float(row["amount"])
            direction = row["type"].strip().lower()  # "debit" / "credit"

            category, score = categorize(description)
            ref_match = _REF_PATTERN.search(description)

            txn = {
                "id": f"t_{i:03d}",
                "date": row["date"].strip(),
                "amount": amount,
                "direction": direction,
                "description": description,
                "source": "bank",
                "category": category,
                "flow_type": guess_flow_type(description, direction),
                "is_recurring": False,          # stub -> Hackathon Final task 8
                "recurring_id": None,           # stub -> Hackathon Final task 8
                "confidence_score": round(score, 2),
                "confidence_label": confidence_label(score),
                "ref_id": ref_match.group(1) if ref_match else None,
            }
            transactions.append(txn)

    return transactions


if __name__ == "__main__":
    here = Path(__file__).parent
    csv_path = here / "sample_data" / "bank_sample.csv"
    out_path = here / "sample_data" / "sample_clean.json"

    result = process_csv(str(csv_path))

    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)

    # ---- quick sanity report, printed for review ----
    print(f"Processed {len(result)} rows -> {out_path}\n")

    label_counts = {}
    for t in result:
        label_counts[t["confidence_label"]] = label_counts.get(t["confidence_label"], 0) + 1
    print("Confidence label breakdown:", label_counts)

    print("\nRows worth checking by eye:")
    for t in result:
        if t["confidence_label"] != "Confirmed" or t["category"] == "Uncategorized":
            print(f"  [{t['confidence_label']:9s}] {t['description']:45s} -> {t['category']} ({t['confidence_score']})")
