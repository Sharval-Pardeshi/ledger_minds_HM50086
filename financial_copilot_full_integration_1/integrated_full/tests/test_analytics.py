"""Unit tests for P2's analyze(). Every expected number is worked out by hand."""
import pytest

from backend.modules.p2.analytics import analyze


def tx(id_, date, amount, direction, category="Food", score=0.92, **extra):
    return {"id": id_, "date": date, "amount": amount, "direction": direction,
            "category": category, "confidence_score": score, **extra}


# 2 months. Income 20,000 + 20,000. Spend 6,000 (Jan) + 10,000 (Feb).
BASIC = [
    tx("a", "2026-01-01", 20000, "credit", "Income"),
    tx("b", "2026-01-10", 6000, "debit", "Rent"),
    tx("c", "2026-02-01", 20000, "credit", "Income"),
    tx("d", "2026-02-10", 10000, "debit", "Rent"),
]


def test_core_numbers():
    r = analyze(BASIC)
    assert r["balance"] == 24000            # 40,000 - 16,000
    assert r["months_covered"] == 2
    assert r["avg_expense"] == 8000         # 16,000 / 2
    assert r["buffer_months"] == 3.0        # 24,000 / 8,000


def test_opening_balance_is_added():
    r = analyze(BASIC, opening_balance=8000)
    assert r["balance"] == 32000
    assert r["buffer_months"] == 4.0


def test_gap_month_still_counts_in_average():
    # Jan and Mar only: 3 calendar months, so 9,000 / 3 = 3,000 (not 4,500)
    data = [tx("a", "2026-01-05", 3000, "debit"), tx("b", "2026-03-05", 6000, "debit")]
    assert analyze(data)["avg_expense"] == 3000


def test_card_bill_and_self_transfer_are_not_expenses():
    data = BASIC + [
        tx("e", "2026-02-11", 5000, "debit", "Card", flow_type="card_bill_payment"),
        tx("f", "2026-02-12", 2000, "debit", "Transfer", flow_type="self_transfer"),
    ]
    r = analyze(data)
    assert r["total_expense"] == 16000      # unchanged
    assert r["balance"] == 17000            # but real cash still left the account


def test_negative_balance_gives_zero_buffer():
    data = [tx("a", "2026-01-01", 1000, "credit"), tx("b", "2026-01-02", 5000, "debit")]
    r = analyze(data)
    assert r["balance"] == -4000
    assert r["buffer_months"] == 0


def test_no_spending_gives_none_not_a_crash():
    r = analyze([tx("a", "2026-01-01", 1000, "credit", "Income")])
    assert r["avg_expense"] == 0
    assert r["buffer_months"] is None
    assert r["data_quality"] is None


def test_category_breakdown_sorted_with_percentages():
    r = analyze(BASIC + [tx("e", "2026-02-15", 4000, "debit", "Food")])
    assert [c["category"] for c in r["category_breakdown"]] == ["Rent", "Food"]
    assert r["category_breakdown"][0]["percent"] == 80.0   # 16,000 of 20,000


def test_data_quality_is_amount_weighted():
    data = [tx("a", "2026-01-01", 900, "debit", score=1.0),
            tx("b", "2026-01-02", 100, "debit", "Uncategorized", score=0.4)]
    r = analyze(data)
    assert r["data_quality"] == 0.94        # (900*1.0 + 100*0.4) / 1000
    assert r["uncertain_rows"] == 1


@pytest.mark.parametrize("bad, message", [
    ([], "No transactions"),
    ([{"id": "x"}], "missing fields"),
    ([tx("x", "2026-01-01", 10, "sideways")], "direction"),
    ([tx("x", "2026-01-01", -5, "debit")], "amount"),
    ([tx("x", "01/01/2026", 10, "debit")], "date"),
])
def test_bad_input_fails_with_clear_message(bad, message):
    with pytest.raises(ValueError, match=message):
        analyze(bad)
