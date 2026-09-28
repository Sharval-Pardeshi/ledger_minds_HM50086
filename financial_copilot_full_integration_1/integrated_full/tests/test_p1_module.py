"""
test_p1_module.py - P1's own unit tests (from p1.zip), run through the
project's real pytest suite against the module as it now lives in
backend/modules/p1/, plus a check on the process_csv_text() wrapper that
the rest of the app actually calls.
"""
from pathlib import Path

from backend.modules.p1 import categorize, confidence_label, process_csv, process_csv_text

CSV_PATH = Path(__file__).resolve().parent.parent / "backend" / "modules" / "p1" / "sample_data" / "bank_sample.csv"


def test_confidence_bands():
    assert confidence_label(0.95) == "Confirmed"
    assert confidence_label(0.85) == "Confirmed"
    assert confidence_label(0.84) == "Likely"
    assert confidence_label(0.60) == "Likely"
    assert confidence_label(0.59) == "Uncertain"


def test_known_merchant_gets_high_confidence():
    category, score = categorize("NETFLIX.COM")
    assert category == "Subscriptions"
    assert score >= 0.85


def test_ambiguous_merchant_gets_medium_confidence():
    category, score = categorize("AMAZON.IN")
    assert category == "Shopping"
    assert 0.60 <= score < 0.85


def test_unknown_merchant_is_uncategorized():
    category, score = categorize("UPI/RANDOM MERCHANT XYZ")
    assert category == "Uncategorized"
    assert score < 0.60


def test_process_csv_returns_correct_row_count():
    result = process_csv(str(CSV_PATH))
    assert len(result) == 40


def test_process_csv_output_matches_contract_shape():
    result = process_csv(str(CSV_PATH))
    required_fields = {
        "id", "date", "amount", "direction", "description", "source",
        "category", "flow_type", "is_recurring", "recurring_id",
        "confidence_score", "confidence_label", "ref_id",
    }
    for txn in result:
        assert required_fields.issubset(txn.keys())


def test_duplicate_row_is_present_unchanged():
    result = process_csv(str(CSV_PATH))
    dup_desc = "UPI/9988776655/RAKESH"
    matches = [t for t in result if t["description"] == dup_desc]
    assert len(matches) == 2


def test_process_csv_text_matches_process_csv():
    """The wrapper pipeline.py actually calls must agree with the real function."""
    from_path = process_csv(str(CSV_PATH))
    from_text = process_csv_text(CSV_PATH.read_text())
    assert from_path == from_text
