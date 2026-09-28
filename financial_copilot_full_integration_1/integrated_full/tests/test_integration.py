"""
test_integration.py - the full P1 -> P2 -> P3 seam, end to end through the
real HTTP API, using P1's actual sample dataset (bank_sample.csv), not a
hand-typed fixture.
"""
import pytest
from fastapi.testclient import TestClient

from backend.main import STATE, app

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_state():
    STATE["result"] = None
    STATE["profile"] = {}
    yield


def load_sample():
    return client.post("/load-sample")


def test_root_serves_the_p4_dashboard():
    r = client.get("/")
    assert r.status_code == 200
    assert "Financial Health Copilot" in r.text


def test_load_sample_runs_the_whole_p1_p2_p3_chain():
    r = load_sample()
    assert r.status_code == 200
    body = r.json()
    assert body["summary"]["transaction_count"] == 40          # P1's 40-row sample
    assert body["summary"]["balance"] == 23987.0
    assert body["recommendation"]["type"] == "emergency_buffer"  # buffer is 0.54mo, well under 3


def test_transactions_endpoint_returns_p1s_real_categories():
    load_sample()
    rows = client.get("/transactions").json()["transactions"]
    assert len(rows) == 40
    categories = {r["category"] for r in rows}
    assert "Loan/EMI" in categories and "Investments" in categories  # P1's real rule set


def test_recommendations_endpoint_returns_gated_list():
    load_sample()
    recs = client.get("/recommendations").json()["recommendations"]
    assert recs[0]["tier"] == "safety"
    assert all("gate" in r for r in recs)


def test_commitments_reflects_detected_recurring_series():
    load_sample()
    commit = client.get("/commitments").json()
    names = {r["name"] for r in commit["recurring"]}
    # EMI, Netflix, SIP all repeat monthly in the sample data -> auto-detected.
    assert "NETFLIX.COM" in names
    assert "EDU LOAN EMI AUTO DEBIT" in names
    assert commit["loans"] == []   # no loan CSV/PDF source in the prototype yet


def test_forecast_and_debt_before_profile():
    load_sample()
    assert "balance_before_salary" in client.get("/forecast").json()
    debt = client.get("/debt").json()
    assert debt["total_emi"] == 0.0   # loans need /profile (see adapter.py)


def test_profile_adds_loan_and_unlocks_arbitrage():
    client.post("/load-sample", params={"opening_balance": 150000})
    client.post("/profile", json={"loans": [{"name": "Card", "emi": 2000, "rate": 30, "outstanding": 50000}],
                                   "days_to_salary": 10})
    debt = client.get("/debt").json()
    assert debt["total_emi"] == 2000
    recs = client.get("/recommendations").json()["recommendations"]
    assert any(r["type"] == "debt_arbitrage" for r in recs)


def test_whatif_cancelling_netflix_lowers_expense():
    load_sample()
    w = client.post("/whatif", json={"cancel": "NETFLIX.COM"}).json()
    assert w["after"]["monthly_expense"] == pytest.approx(w["before"]["monthly_expense"] - 649, abs=0.01)


def test_chat_answers_are_tagged_and_masked():
    load_sample()
    r = client.post("/chat", json={"message": "what is my buffer, acct 123456789012?"}).json()
    assert r["label"] == "Fact"
    assert "123456789012" not in r["text"]


def test_confirm_rejecting_a_series_removes_it_from_recommendations():
    load_sample()
    # Netflix is auto-detected but starts "in use"; seed it unused to get a
    # subscription-optimizer recommendation the same way the demo would.
    client.post("/profile", json={"recurring_overrides": {"t_004": {"unused": True, "conf": 0.5}}})
    sub = next(r for r in client.get("/recommendations").json()["recommendations"]
               if r["type"] == "subscription_optimizer")
    assert sub["gate"]["action"] == "ask"

    client.post("/confirm", json={"series": sub["series"], "confirmed": False})
    recs_after = client.get("/recommendations").json()["recommendations"]
    assert not any(r["type"] == "subscription_optimizer" for r in recs_after)


def test_bad_csv_is_rejected_with_clear_message():
    r = client.post("/upload", files={"file": ("bad.csv", b"date,amount\n2026-01-01,10\n", "text/csv")})
    assert r.status_code == 400
