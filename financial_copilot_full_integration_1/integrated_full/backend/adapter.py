"""
adapter.py - the P2 -> P3 integration seam (Doc 02, "Integration seam B").

P3's engine (engine.py) was designed and tested against a hand-written
`recurring`/`loans` structure (see the `BASE` object in
p3_test_lab_prototype.html), not against raw CleanTransactions. Real P1
output only tells us about individual transaction rows.

`build_engine_input()` bridges that gap for the prototype:
  - Recurring payments are *detected* from the transaction history itself
    (same description, appearing in >= 2 different months, consistent
    amount) rather than assumed. This is a lightweight stand-in for the
    Final build's dedicated `detect_recurring()` (Doc 02, P1 task #8).
  - Loans and a planned purchase are NOT derivable from a bank/UPI CSV at
    all (they need their own CSV/PDF sources per Doc 01 section 3, out of
    prototype scope) - so they are accepted as optional, explicit input
    via POST /profile and simply merged in. Everything else keeps working
    with sensible defaults (empty loans, no planned purchase) if /profile
    is never called.

Nothing here changes P1's or P2's existing contracts: this only adds a new
derived shape for P3's engine to consume.
"""
from __future__ import annotations

from collections import defaultdict

NON_SPEND_FLOWS = {"card_bill_payment", "self_transfer"}
RECURRING_KIND_BY_CATEGORY = {"Rent": "rent", "Subscriptions": "subscription"}
AMOUNT_TOLERANCE_FRACTION = 0.15  # +/- 15% is still "the same" recurring amount


def _detect_recurring(transactions: list[dict]) -> tuple[list[dict], float]:
    """Group same-description debits across >=2 distinct months into recurring
    series. Returns (recurring_list, leftover_variable_total)."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for t in transactions:
        if t["direction"] != "debit" or t.get("flow_type", "real_expense") in NON_SPEND_FLOWS:
            continue
        groups[t["description"].strip().lower()].append(t)

    recurring = []
    variable_total = 0.0
    for rows in groups.values():
        months = {r["date"][:7] for r in rows}
        amounts = [r["amount"] for r in rows]
        avg_amount = sum(amounts) / len(amounts)
        consistent = (max(amounts) - min(amounts)) <= AMOUNT_TOLERANCE_FRACTION * avg_amount + 1
        if len(rows) >= 2 and len(months) >= 2 and consistent:
            category = rows[0]["category"]
            recurring.append({
                "id": rows[0]["id"],
                "name": rows[0]["description"],
                "kind": RECURRING_KIND_BY_CATEGORY.get(category, "other"),
                "amount": round(avg_amount, 2),
                "conf": round(sum(r["confidence_score"] for r in rows) / len(rows), 2),
                # No usage-signal source in the prototype yet, so a freshly
                # detected series starts as "in use". A person can flag it
                # unused (or the demo/profile endpoint can seed one) so the
                # Subscription Optimizer has something to reason about.
                "unused": False,
            })
        else:
            variable_total += sum(amounts)
    return recurring, variable_total


def build_engine_input(transactions: list[dict], summary: dict, profile: dict | None = None) -> dict:
    """transactions + summary (P2's existing contracts) -> `d` for engine.py.

    `profile` is the optional extra the prototype can't derive from a CSV:
    {"days_to_salary": int, "loans": [...], "planned": {...},
     "income_override": float, "recurring_overrides": {id: {...}}}.
    """
    profile = profile or {}
    recurring, variable_total = _detect_recurring(transactions)

    overrides = profile.get("recurring_overrides") or {}
    for r in recurring:
        if r["id"] in overrides:
            r.update(overrides[r["id"]])
    # A profile can also add recurring items the auto-detector could not see
    # yet (e.g. only one statement month uploaded so far).
    recurring += profile.get("extra_recurring", [])

    months = summary.get("months_covered") or 1
    variable_expense = round(variable_total / months, 2)
    income = profile.get("income_override")
    if income is None:
        income = round(summary.get("total_income", 0) / months, 2)

    return {
        "balance": summary["balance"],
        "income": income,
        "days_to_salary": profile.get("days_to_salary", 15),
        "variable_expense": variable_expense,
        "data_quality": summary.get("data_quality") if summary.get("data_quality") is not None else 0.9,
        "recurring": recurring,
        "loans": profile.get("loans", []),
        "planned": profile.get("planned"),
    }
