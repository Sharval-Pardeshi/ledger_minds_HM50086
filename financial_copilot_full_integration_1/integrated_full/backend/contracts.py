"""
contracts.py - the "shared language" of the team.

Everything here mirrors Doc 01, section 1 (CleanTransaction + confidence bands).
P2 uses it as a guard at the P1 -> P2 seam: if P1 hands over a badly shaped row,
we fail loudly with a clear message instead of producing wrong numbers.
"""
from datetime import date

# ---- Confidence bands (Doc 01) -------------------------------------------
CONFIRMED_MIN = 0.85   # >= 0.85           -> "Confirmed"
LIKELY_MIN = 0.60      # 0.60 <= x < 0.85  -> "Likely"; below -> "Uncertain"


def confidence_label(score: float) -> str:
    """Turn a 0-1 score into the label the UI shows."""
    if score >= CONFIRMED_MIN:
        return "Confirmed"
    if score >= LIKELY_MIN:
        return "Likely"
    return "Uncertain"


# ---- CleanTransaction -----------------------------------------------------
# Fields P2 cannot work without. Other contract fields are allowed and ignored.
REQUIRED_FIELDS = ("id", "date", "amount", "direction", "category", "confidence_score")
VALID_DIRECTIONS = ("debit", "credit")


def validate_transactions(transactions: list[dict]) -> None:
    """Raise ValueError (with the offending row id) if a row breaks the contract."""
    if not isinstance(transactions, list) or not transactions:
        raise ValueError("No transactions to analyse.")

    for i, t in enumerate(transactions):
        row = t.get("id", f"row #{i + 1}")
        missing = [f for f in REQUIRED_FIELDS if f not in t]
        if missing:
            raise ValueError(f"Transaction {row} is missing fields: {', '.join(missing)}")
        if t["direction"] not in VALID_DIRECTIONS:
            raise ValueError(f"Transaction {row}: direction must be 'debit' or 'credit'")
        if not isinstance(t["amount"], (int, float)) or t["amount"] < 0:
            raise ValueError(f"Transaction {row}: amount must be a non-negative number")
        try:
            date.fromisoformat(t["date"])
        except (TypeError, ValueError):
            raise ValueError(f"Transaction {row}: date must look like YYYY-MM-DD")
