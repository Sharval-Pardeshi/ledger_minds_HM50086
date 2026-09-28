"""
Basic unit tests for process_csv() -- team's Definition of Done requires
"at least a few unit tests on the core logic."

Run with: python3 -m pytest test_process_csv.py -v
(or just: python3 test_process_csv.py)
"""
from process_csv import process_csv, categorize, confidence_label
from pathlib import Path

CSV_PATH = Path(__file__).parent / "sample_data" / "bank_sample.csv"


def test_confidence_bands():
    assert confidence_label(0.95) == "Confirmed"
    assert confidence_label(0.85) == "Confirmed"
    assert confidence_label(0.84) == "Likely"
    assert confidence_label(0.60) == "Likely"
    assert confidence_label(0.59) == "Uncertain"
    assert confidence_label(0.10) == "Uncertain"


def test_known_merchant_gets_high_confidence():
    category, score = categorize("NETFLIX.COM")
    assert category == "Subscriptions"
    assert score >= 0.85


def test_ambiguous_merchant_gets_medium_confidence():
    # Amazon sells everything -- should be Likely, not Confirmed
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
    # Prototype does NOT dedup (that's Hackathon Final task 6) -- both
    # copies of the deliberate duplicate should come through as-is.
    result = process_csv(str(CSV_PATH))
    dup_desc = "UPI/9988776655/RAKESH"
    matches = [t for t in result if t["description"] == dup_desc]
    assert len(matches) == 2


def test_salary_detected_as_income():
    result = process_csv(str(CSV_PATH))
    salary_rows = [t for t in result if t["category"] == "Income"]
    assert len(salary_rows) == 2  # one per month
    for row in salary_rows:
        assert row["flow_type"] == "income"
        assert row["confidence_label"] == "Confirmed"


def test_ref_id_extracted_from_upi_description():
    category, _ = categorize("UPI/408213445/RAJESH KUMAR/RENT MAY")
    assert category == "Rent"
    result = process_csv(str(CSV_PATH))
    rent_row = next(t for t in result if t["category"] == "Rent")
    assert rent_row["ref_id"] == "408213445"


if __name__ == "__main__":
    import sys
    tests = [obj for name, obj in list(globals().items()) if name.startswith("test_")]
    passed, failed = 0, 0
    for test in tests:
        try:
            test()
            print(f"PASS  {test.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"FAIL  {test.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
