"""
STAND-IN for Person 1's  process_csv(file) -> list[CleanTransaction].

Why it exists: P2 must be able to run and test the whole flow before P1 finishes.
When P1's real function is ready, delete this file and change ONE import in
backend/pipeline.py. The output shape is identical (the contract).
"""
import csv
from datetime import datetime

from ..contracts import confidence_label

KEYWORD_RULES = [  # (keyword in description, category)
    ("salary", "Income"),
    ("swiggy", "Food"), ("zomato", "Food"),
    ("bigbasket", "Groceries"), ("grocery", "Groceries"), ("dmart", "Groceries"),
    ("rent", "Rent"),
    ("netflix", "Subscriptions"), ("spotify", "Subscriptions"), ("prime", "Subscriptions"),
    ("uber", "Transport"), ("ola", "Transport"), ("metro", "Transport"),
    ("electricity", "Utilities"), ("water bill", "Utilities"), ("broadband", "Utilities"),
    ("atm", "Cash Withdrawal"),
]
MATCH_CONFIDENCE = 0.92      # a keyword matched
NO_MATCH_CONFIDENCE = 0.40   # nothing matched -> "Uncategorized", low trust
DATE_FORMATS = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y")
REQUIRED_COLUMNS = {"date", "description", "amount", "type"}


def _parse_date(text: str) -> str:
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text.strip(), fmt).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f"Unrecognised date '{text}' (use YYYY-MM-DD or DD/MM/YYYY)")


def _categorize(description: str, direction: str) -> tuple[str, float]:
    desc = description.lower()
    for keyword, category in KEYWORD_RULES:
        if keyword in desc:
            return category, MATCH_CONFIDENCE
    if direction == "credit":
        return "Other Income", 0.60
    return "Uncategorized", NO_MATCH_CONFIDENCE


def process_csv(file) -> list[dict]:
    """`file` is any text file-like object (open(...) or io.StringIO)."""
    reader = csv.DictReader(file)
    if not reader.fieldnames:
        raise ValueError("The CSV file is empty.")
    headers = {h.strip().lower() for h in reader.fieldnames}
    missing = REQUIRED_COLUMNS - headers
    if missing:
        raise ValueError(f"CSV is missing column(s): {', '.join(sorted(missing))}. "
                         f"Expected: date, description, amount, type")

    transactions = []
    for n, raw in enumerate(reader, start=1):
        row = {k.strip().lower(): (v or "").strip() for k, v in raw.items() if k}
        try:
            amount = abs(float(row["amount"].replace(",", "").replace("₹", "")))
        except ValueError:
            raise ValueError(f"Row {n}: amount '{row['amount']}' is not a number")
        kind = row["type"].lower()
        if kind in ("credit", "cr"):
            direction = "credit"
        elif kind in ("debit", "dr"):
            direction = "debit"
        else:
            raise ValueError(f"Row {n}: type must be credit or debit, got '{row['type']}'")

        category, score = _categorize(row["description"], direction)
        transactions.append({
            "id": f"t_{n:03d}",
            "date": _parse_date(row["date"]),
            "amount": amount,
            "direction": direction,
            "description": row["description"],
            "source": "bank",
            "category": category,
            "flow_type": "income" if direction == "credit" else "real_expense",
            "is_recurring": False,        # recurring detection is out of prototype scope
            "recurring_id": None,
            "confidence_score": score,
            "confidence_label": confidence_label(score),
            "ref_id": None,
        })
    return transactions
