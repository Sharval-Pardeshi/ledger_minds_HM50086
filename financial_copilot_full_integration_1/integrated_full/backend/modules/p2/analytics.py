"""
analytics.py - PERSON 2's core deliverable for the prototype.

    analyze(transactions) -> {balance, avg_expense, buffer_months, ...}

Pure function: list in, dict out. No web code, no files, no database.
That makes it easy to test by hand and easy to reuse later as part of
`recompute()` (Final build, P2 task #6).
"""
from collections import defaultdict
from datetime import date

from ...contracts import confidence_label, validate_transactions

# Money that moved but was not really "spent". P1's prototype does not label
# these yet, but the Final build will, so we already ignore them for expenses.
NON_SPEND_FLOWS = {"card_bill_payment", "self_transfer"}


def _is_expense(t: dict) -> bool:
    """A debit that counts as real spending."""
    return t["direction"] == "debit" and t.get("flow_type", "real_expense") not in NON_SPEND_FLOWS


def _months_covered(transactions: list[dict]) -> int:
    """Calendar months from the earliest to the latest transaction (inclusive).

    Jul 1 -> Sep 30 = 3.  A month with no rows in the middle still counts,
    which is the honest way to average spending.
    """
    dates = [date.fromisoformat(t["date"]) for t in transactions]
    first, last = min(dates), max(dates)
    return (last.year - first.year) * 12 + (last.month - first.month) + 1


def analyze(transactions: list[dict], opening_balance: float = 0.0) -> dict:
    """Compute the numbers the dashboard and the recommendation rule need.

    balance        = opening_balance + all credits - all debits
    avg_expense    = total real expenses / months covered
    buffer_months  = balance / avg_expense   (0 if balance is negative,
                                              None if there is no spending)
    """
    validate_transactions(transactions)

    total_income = sum(t["amount"] for t in transactions if t["direction"] == "credit")
    total_debits = sum(t["amount"] for t in transactions if t["direction"] == "debit")
    balance = opening_balance + total_income - total_debits

    expenses = [t for t in transactions if _is_expense(t)]
    total_expense = sum(t["amount"] for t in expenses)
    months = _months_covered(transactions)
    avg_expense = total_expense / months

    buffer_months = None if avg_expense == 0 else max(balance, 0) / avg_expense

    # Spending by category (feeds P4's chart)
    by_cat = defaultdict(float)
    for t in expenses:
        by_cat[t["category"]] += t["amount"]
    breakdown = [
        {
            "category": cat,
            "amount": round(amt, 2),
            "percent": round(100 * amt / total_expense, 1) if total_expense else 0.0,
        }
        for cat, amt in sorted(by_cat.items(), key=lambda kv: -kv[1])
    ]

    # Data quality: how much of the SPENDING is backed by confident categories.
    # Weighted by amount, so one small unclear row matters less than a big one.
    if total_expense:
        data_quality = sum(t["amount"] * t["confidence_score"] for t in expenses) / total_expense
    else:
        data_quality = None
    uncertain_rows = sum(1 for t in transactions if confidence_label(t["confidence_score"]) == "Uncertain")

    return {
        # --- the three agreed keys (Doc 02, P2 prototype deliverable) ---
        "balance": round(balance, 2),
        "avg_expense": round(avg_expense, 2),
        "buffer_months": None if buffer_months is None else round(buffer_months, 2),
        # --- extra fields (contracts allow adding, never renaming) ---
        "months_covered": months,
        "total_income": round(total_income, 2),
        "total_expense": round(total_expense, 2),
        "opening_balance": round(opening_balance, 2),
        "category_breakdown": breakdown,
        "data_quality": None if data_quality is None else round(data_quality, 2),
        "data_quality_label": None if data_quality is None else confidence_label(data_quality),
        "uncertain_rows": uncertain_rows,
        "transaction_count": len(transactions),
    }
