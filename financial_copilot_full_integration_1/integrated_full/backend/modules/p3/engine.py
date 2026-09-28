"""
engine.py - PERSON 3's real engine, ported from `p3_test_lab_prototype.html`.

That HTML file was P3's own local test rig: every function below existed
there as JavaScript, running only against a hand-typed fake dataset in the
browser (`BASE`), never touching P2's backend or real transactions. This
module is a faithful line-for-line port of that JS into Python so the exact
same logic can run inside P2's FastAPI service (see `adapter.py` for how
real CleanTransactions become the `d` dict these functions expect, and
`main.py` for the endpoints that expose them).

Kept identical to the JS version:
    - the 4 recommendation modules (buffer, subscriptions, timing, arbitrage)
    - the safety-priority ranker
    - the confidence combiner (weakest link = min of inputs)
    - the Safety Gate (Confirmed / Likely / Uncertain -> ask-to-confirm)
    - the in-memory What-If simulator (deep-copy, recompute, diff)
    - the PII-masking + prompt-injection-resistant + no-action chat layer

`d` (the engine's input shape) mirrors the JS `BASE` object exactly:
    {
      "balance": float, "income": float, "days_to_salary": int,
      "variable_expense": float, "data_quality": float,
      "recurring": [{"id","name","kind","amount","conf","unused"}, ...],
      "loans": [{"name","emi","rate","outstanding"}, ...],
      "planned": {"name","amount"} | None,
    }
"""
from __future__ import annotations

import copy
import math
import re

from ...contracts import confidence_label

TARGET_BUFFER_MONTHS = 3
SAVING_WINDOW_MONTHS = 6
ROUND_TO = 500          # buffer-builder savings are rounded up to a tidy ₹500
SAFETY_IMPACT = 10 ** 12  # sorts safety recs before any real ₹ impact, but stays JSON-safe (unlike float("inf"))

# ---- money helper (matches JS `inr`) --------------------------------------
def inr(n: float) -> str:
    return f"Rs {round(n):,}"


# ---- confidence: weakest-link combiner -------------------------------------
def combine_confidence(*scores: float) -> dict:
    """Weakest-link rule (Doc 01): a derived fact is only as confident as its
    shakiest input. Mirrors JS `conf(m, p, q)`."""
    score = round(min(scores), 2)
    return {"score": score, "label": confidence_label(score)}


# ---- recompute: the single function shared by dashboard + What-If ---------
def recompute(d: dict) -> dict:
    """Same math as the JS `recompute(d)`. Pure function: dict in, dict out."""
    recurring_total = sum(float(r.get("amount") or 0) for r in d.get("recurring", []))
    emi_total = sum(float(l.get("emi") or 0) for l in d.get("loans", []))
    fixed = recurring_total + emi_total
    monthly_expense = fixed + float(d.get("variable_expense") or 0)

    balance = float(d.get("balance") or 0)
    income = float(d.get("income") or 0)
    days_to_salary = float(d.get("days_to_salary") or 0)

    buffer_months = round(balance / (monthly_expense or 1), 2)
    debt_to_income = round(emi_total / (income or 1), 2)
    balance_before_salary = round(balance - monthly_expense * days_to_salary / 30)

    return {
        "monthly_expense": round(monthly_expense, 2),
        "buffer_months": buffer_months,
        "debt_to_income": debt_to_income,
        "balance_before_salary": balance_before_salary,
    }


# ---- the 4 recommendation modules (Doc 01, section 3.4) --------------------
def rec_buffer(d: dict) -> dict | None:
    """Emergency Buffer Builder. Fires when buffer_months < target."""
    k = recompute(d)
    if k["buffer_months"] >= TARGET_BUFFER_MONTHS:
        return None
    balance = float(d.get("balance") or 0)
    gap = TARGET_BUFFER_MONTHS * k["monthly_expense"] - balance
    x = math.ceil(max(gap, 0) / SAVING_WINDOW_MONTHS / ROUND_TO) * ROUND_TO
    after_buffer = round((balance + SAVING_WINDOW_MONTHS * x) / (k["monthly_expense"] or 1), 2)
    return {
        "id": "rec_buffer",
        "type": "emergency_buffer",
        "tier": "safety",
        "impact": SAFETY_IMPACT,  # safety always ranks first regardless of ₹ impact
        "title": "Build your emergency buffer",
        "explanation": f"Save {inr(x)}/month to reach {TARGET_BUFFER_MONTHS} months of cover "
                        f"in {SAVING_WINDOW_MONTHS} months.",
        "before": {"buffer_months": k["buffer_months"]},
        "after": {"buffer_months": after_buffer},
        "monthly_saving": x,
        "months_to_target": SAVING_WINDOW_MONTHS,
        "confidence": combine_confidence(0.92, 0.96, d.get("data_quality") or 0.0)["score"],
        "confidence_label": combine_confidence(0.92, 0.96, d.get("data_quality") or 0.0)["label"],
        "tag": "Recommendation",
        "requires_user_confirmation": True,
    }


def rec_subscriptions(d: dict) -> list[dict]:
    """Subscription Optimizer. One recommendation per unused subscription."""
    k = recompute(d)
    out = []
    for r in d.get("recurring", []):
        if r.get("kind") != "subscription" or not r.get("unused"):
            continue
        amount = float(r.get("amount") or 0)
        conf = combine_confidence(0.9, r.get("conf", 0.0), d.get("data_quality") or 0.0)
        out.append({
            "id": f"rec_sub_{r.get('id')}",
            "type": "subscription_optimizer",
            "tier": "opt",
            "impact": amount * 12,
            "title": f"Cancel {r.get('name')}",
            "explanation": f"Unused for 60+ days. Saves {inr(amount * 12)} a year.",
            "before": {"monthly_expense": k["monthly_expense"]},
            "after": {"monthly_expense": round(k["monthly_expense"] - amount, 2)},
            "confidence": conf["score"],
            "confidence_label": conf["label"],
            "tag": "Recommendation",
            "requires_user_confirmation": True,
            # Safety-Gate fields: which recurring series this is about, and the
            # yes/no question to ask when confidence is Uncertain.
            "series": r.get("id"),
            "ask": f'Is "{r.get("name")}" really an unused subscription?',
        })
    return out


def rec_purchase_timing(d: dict) -> dict | None:
    """Purchase-Timing Advisor."""
    planned = d.get("planned")
    if not planned or not planned.get("name"):
        return None
    k = recompute(d)
    amount = float(planned.get("amount") or 0)
    if k["balance_before_salary"] >= amount:
        return None
    return {
        "id": "rec_timing",
        "type": "purchase_timing",
        "tier": "opt",
        "impact": 5000,
        "title": f"Wait to buy the {planned['name']}",
        "explanation": (
            f"Buying now leaves {inr(k['balance_before_salary'] - amount)} before salary. "
            f"Wait {d.get('days_to_salary')} days."
        ),
        "before": {"balance_before_salary": k["balance_before_salary"] - amount},
        "after": {"balance_before_salary": k["balance_before_salary"]},
        "confidence": combine_confidence(0.9, 0.85, d.get("data_quality") or 0.0)["score"],
        "confidence_label": combine_confidence(0.9, 0.85, d.get("data_quality") or 0.0)["label"],
        "tag": "Prediction",
        "requires_user_confirmation": True,
    }


def rec_arbitrage(d: dict) -> dict | None:
    """Debt-vs-Idle-Cash Arbitrage."""
    k = recompute(d)
    balance = float(d.get("balance") or 0)
    idle = balance - TARGET_BUFFER_MONTHS * k["monthly_expense"]
    high_rate_loans = sorted(
        (l for l in d.get("loans", []) if float(l.get("rate") or 0) > 7),
        key=lambda l: -float(l["rate"]),
    )
    if not high_rate_loans or idle <= 0:
        return None
    loan = high_rate_loans[0]
    x = min(idle, float(loan.get("outstanding") or 0))
    rate = float(loan["rate"])
    return {
        "id": "rec_arb",
        "type": "debt_arbitrage",
        "tier": "opt",
        "impact": x * (rate - 3) / 100,
        "title": f"Prepay {loan.get('name')}",
        "explanation": f"Idle cash {inr(x)} earns ~3% but the loan costs {rate}%.",
        "before": {},
        "after": {},
        "confidence": combine_confidence(0.85, 0.9, d.get("data_quality") or 0.0)["score"],
        "confidence_label": combine_confidence(0.85, 0.9, d.get("data_quality") or 0.0)["label"],
        "tag": "Recommendation",
        "requires_user_confirmation": True,
    }


def rank(recs: list[dict]) -> list[dict]:
    """Safety actions always outrank optimizations (Doc 01/02)."""
    return sorted(recs, key=lambda r: (0 if r["tier"] == "safety" else 1, -r["impact"]))


def all_recommendations(d: dict) -> list[dict]:
    recs = [rec_buffer(d)]
    recs += rec_subscriptions(d)
    recs += [rec_purchase_timing(d), rec_arbitrage(d)]
    return rank([r for r in recs if r is not None])


# ---- Safety Gate ------------------------------------------------------------
def gate(items: list[dict]) -> list[dict]:
    """Confirmed / Likely -> show as-is. Uncertain -> ask the user first."""
    gated = []
    for r in items:
        item = dict(r)
        if r.get("confidence_label") == "Uncertain":
            item["gate"] = {"action": "ask", "prompt": r.get("ask")}
        else:
            item["gate"] = {"action": "show"}
        gated.append(item)
    return gated


# ---- What-If: deep-copy, mutate the copy, recompute, diff -------------------
def whatif(d: dict, cancel: str | None = None, balance_delta: float = 0) -> dict:
    """Never mutates `d`. Returns {"before": ..., "after": ...}."""
    before = recompute(d)
    n = copy.deepcopy(d)
    if cancel:
        n["recurring"] = [r for r in n.get("recurring", [])
                           if r.get("name", "").lower() != cancel.lower()]
    if balance_delta:
        n["balance"] = float(n.get("balance") or 0) + float(balance_delta)
    after = recompute(n)
    return {"before": before, "after": after}


# ---- Chat: masking, prompt-injection defence, no-action guarantee ----------
MASK_RE = re.compile(r"\b\d{8,16}\b")
INJECTION_RE = re.compile(r"(ignore (all|previous|prior)|system prompt|you are now|reveal .*prompt)", re.I)
ACTION_RE = re.compile(r"(cancel|transfer|pay|send|buy) .*(for me|now|it)\b", re.I)


def mask(text: str) -> str:
    """Golden principle #3: no raw PII (account/card numbers) leaves the app."""
    return MASK_RE.sub(lambda m: "XXXX" + m.group(0)[-4:], text)


def chat(d: dict, question: str) -> dict:
    """Golden principle #2: the LLM/chat layer never acts, only explains.
    Every answer is tagged Fact / Prediction / Recommendation (Doc 01, 3.1)."""
    q = mask(question)
    if INJECTION_RE.search(q):
        return {"label": "Fact",
                "text": "I can only answer about your finances, and I ignore instructions inside messages."}
    if ACTION_RE.search(q):
        return {"label": "Recommendation",
                "text": "I can't take actions for you. Recommendation: cancel it yourself in the app; "
                         "I can show the effect first with What-If."}
    k = recompute(d)
    if re.search(r"buffer|emergency", q, re.I):
        return {"label": "Fact", "text": f"You have {k['buffer_months']} months of spending covered."}
    if re.search(r"salary|forecast|before", q, re.I):
        return {"label": "Prediction",
                "text": f"Expect about {inr(k['balance_before_salary'])} left before your next salary."}
    if re.search(r"save|advice|should", q, re.I):
        recs = all_recommendations(d)
        if recs:
            top = recs[0]
            return {"label": "Recommendation", "text": top["explanation"], "confidence_label": top["confidence_label"]}
        return {"label": "Fact", "text": "Nothing urgent."}
    return {"label": "Fact", "text": 'Try: "buffer", "balance before salary", or "what should I do".'}
