"""
STAND-IN for Person 3's  recommend(summary) -> Recommendation | None.

The single prototype rule (Doc 01, 2.3 step 5):
    buffer_months < 3  ->  "save X per month", X = (3 * monthly_expense - balance) / 6
Replace with P3's real function at integration; the output shape is the contract.
"""
import math

from ..contracts import confidence_label

TARGET_MONTHS = 3
SAVING_WINDOW_MONTHS = 6


def recommend(summary: dict) -> dict | None:
    buffer_months = summary.get("buffer_months")
    if buffer_months is None or buffer_months >= TARGET_MONTHS:
        return None  # nothing to recommend: buffer is healthy (or no spending data)

    # Use the exact average (total / months), not the rounded display value, and round the
    # gap to paise so float noise like 19294.000000001 can never bump a rupee up.
    exact_avg = summary["total_expense"] / summary["months_covered"]
    gap = round(TARGET_MONTHS * exact_avg - summary["balance"], 2)
    monthly_saving = math.ceil(max(gap, 0) / SAVING_WINDOW_MONTHS)
    confidence = summary.get("data_quality") or 0.0

    return {
        "id": "rec_1",
        "type": "emergency_buffer",
        "title": "Build an emergency fund",
        "explanation": (
            f"You have {buffer_months} months of buffer; the target is {TARGET_MONTHS}. "
            f"Saving Rs {monthly_saving:,}/month for {SAVING_WINDOW_MONTHS} months closes "
            f"the gap of Rs {math.ceil(gap):,}."
        ),
        "label": "Recommendation",
        "confidence": confidence,
        "confidence_label": confidence_label(confidence),
        "before": {"buffer_months": buffer_months},
        "after": {"buffer_months": float(TARGET_MONTHS)},
        "monthly_saving": monthly_saving,
        "months_to_target": SAVING_WINDOW_MONTHS,
        "requires_user_confirmation": True,
    }
