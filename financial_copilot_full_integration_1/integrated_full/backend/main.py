"""
main.py - the integrated backend: P1 -> P2 -> P3, plus P4 served as the root page.

Run from the project root:   uvicorn backend.main:app --reload --port 8000
Dashboard (P4):               http://localhost:8000/
Interactive API docs:         http://localhost:8000/docs

State lives in memory (dict below). Restarting the server clears it -
that is deliberate for the prototype (no DB, no auth).

Endpoints implement the team's agreed API (Doc 02, section 0):
    POST /upload · GET /transactions · GET /forecast · GET /debt ·
    GET /recommendations · POST /whatif · POST /chat · POST /confirm
plus two documented prototype-only additions:
    GET  /commitments - the recurring/loans/planned data P4's "Commitments"
                         panel needs (this IS the P3 engine's `d` input, so
                         it doubles as a debugging window into engine state)
    POST /profile      - loans/planned-purchase/days_to_salary input a bank
                         CSV alone can't provide (see adapter.py docstring)
"""
from pathlib import Path

from fastapi import Body, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .adapter import build_engine_input
from .modules.p3 import all_recommendations, chat as engine_chat, gate, recompute, whatif as engine_whatif
from .pipeline import run_prototype_pipeline

MAX_UPLOAD_BYTES = 2 * 1024 * 1024  # 2 MB is plenty for a prototype CSV
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_CSV = PROJECT_ROOT / "sample_data" / "bank_sample.csv"
P4_INDEX = PROJECT_ROOT / "frontend" / "p4" / "index.html"

app = FastAPI(title="Financial Health Copilot - P1+P2+P3+P4 integrated")

# Prototype-permissive CORS: P4 is served same-origin by this same app (see
# "/" below), so this mainly covers the case where someone serves the P4
# folder separately (e.g. a live-reload dev server) while pointing it at
# this API. Tighten this before anything resembling production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STATE: dict = {"result": None, "profile": {}}   # result: {"transactions","summary","engine_input","recommendations","recommendation"}


def _process(csv_text: str, opening_balance: float) -> dict:
    try:
        result = run_prototype_pipeline(csv_text, opening_balance, STATE["profile"])
    except ValueError as err:                       # P2's own contract checks
        raise HTTPException(status_code=400, detail=str(err))
    except KeyError as err:
        # KNOWN GAP (see docs/P1_P4_Integration_Notes.md): P1's real
        # process_csv() assumes date/description/amount/type columns exist
        # and raises a bare KeyError instead of a clean message if a column
        # is missing. Translated here at the integration boundary rather
        # than edited in P1's file, so P1 stays a drop-in-swappable module.
        raise HTTPException(status_code=400,
                             detail=f"CSV is missing an expected column: {err}. "
                                    f"Expected columns: date, description, amount, type")
    STATE["result"] = result
    return result


def _require_result() -> dict:
    if STATE["result"] is None:
        raise HTTPException(status_code=404, detail="No data yet. POST a CSV to /upload first (or /load-sample).")
    return STATE["result"]


def _refresh_recommendations() -> None:
    """Re-run the P3 engine after /profile or /confirm changes engine_input,
    without re-parsing the CSV or re-running P1/P2."""
    result = STATE["result"]
    recs = gate(all_recommendations(result["engine_input"]))
    result["recommendations"] = recs
    result["recommendation"] = recs[0] if recs else None


# ---- P4: served as the dashboard's home page --------------------------------
@app.get("/")
def dashboard():
    if not P4_INDEX.exists():
        raise HTTPException(status_code=500, detail=f"P4 frontend not found at {P4_INDEX}")
    return FileResponse(P4_INDEX)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/upload")
async def upload(file: UploadFile = File(...), opening_balance: float = 0.0):
    """Upload a CSV (date, description, amount, type). Returns the full result."""
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are supported in the prototype.")
    raw = await file.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 2 MB).")
    try:
        text = raw.decode("utf-8-sig")              # utf-8-sig also strips Excel's hidden BOM
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File is not valid UTF-8 text.")
    result = _process(text, opening_balance)
    return {"summary": result["summary"], "recommendation": result["recommendation"],
            "recommendations": result["recommendations"]}


@app.post("/load-sample")
def load_sample(opening_balance: float = 0.0):
    """One-click demo data (handy for P4 and for the demo)."""
    result = _process(SAMPLE_CSV.read_text(encoding="utf-8-sig"), opening_balance)
    return {"summary": result["summary"], "recommendation": result["recommendation"],
            "recommendations": result["recommendations"]}


@app.get("/summary")
def summary():
    """What P4's dashboard reads: numbers + category chart data + recommendation(s)."""
    result = _require_result()
    return {"summary": result["summary"], "recommendation": result["recommendation"],
            "recommendations": result["recommendations"]}


@app.get("/transactions")
def transactions():
    """Every cleaned row with its category and confidence (for a table or debugging)."""
    return {"transactions": _require_result()["transactions"]}


@app.get("/forecast")
def forecast():
    """Cash-flow forecast: balance expected right before the next salary."""
    d = _require_result()["engine_input"]
    k = recompute(d)
    return {"balance_before_salary": k["balance_before_salary"], "days_to_salary": d["days_to_salary"]}


@app.get("/debt")
def debt():
    """Basic debt analysis: total EMI and debt-to-income."""
    d = _require_result()["engine_input"]
    k = recompute(d)
    total_emi = sum(float(l.get("emi") or 0) for l in d.get("loans", []))
    return {"debt_to_income": k["debt_to_income"], "total_emi": round(total_emi, 2), "loans": d.get("loans", [])}


@app.get("/commitments")
def commitments():
    """Recurring payments, loans and planned purchase - what P4's
    'Recurring Payments, Loans & Planned Purchases' panel renders. This is
    exactly the P3 engine's `d` input (see adapter.py)."""
    return _require_result()["engine_input"]


@app.get("/recommendations")
def recommendations():
    """All 4 modules, ranked (safety first) and safety-gated."""
    return {"recommendations": _require_result()["recommendations"]}


@app.post("/whatif")
def whatif(payload: dict = Body(default={})):
    """{"cancel": "Netflix", "balance_delta": 0} -> before/after, real data untouched."""
    d = _require_result()["engine_input"]
    return engine_whatif(d, cancel=payload.get("cancel"), balance_delta=payload.get("balance_delta", 0))


@app.post("/chat")
def chat_endpoint(payload: dict = Body(...)):
    """{"message": "what is my buffer?"} -> {label, text, ...}. Never executes actions."""
    message = payload.get("message", "")
    if not message.strip():
        raise HTTPException(status_code=400, detail="message is required")
    d = _require_result()["engine_input"]
    return engine_chat(d, message)


@app.post("/confirm")
def confirm(payload: dict = Body(...)):
    """Answer an Uncertain item's safety-gate prompt.
    {"series": "s4", "confirmed": true}  -> keep it, trust it fully (conf = 1.0)
    {"series": "s4", "confirmed": false} -> the person says it's wrong; drop the series
    """
    series = payload.get("series")
    confirmed = payload.get("confirmed")
    if series is None or confirmed is None:
        raise HTTPException(status_code=400, detail="series and confirmed are required")
    result = _require_result()
    recurring = result["engine_input"]["recurring"]
    if confirmed:
        for r in recurring:
            if r["id"] == series:
                r["conf"] = 1.0
    else:
        result["engine_input"]["recurring"] = [r for r in recurring if r["id"] != series]
    _refresh_recommendations()
    return {"recommendations": result["recommendations"]}


@app.post("/profile")
def set_profile(payload: dict = Body(default={})):
    """Prototype-only extension (see adapter.py docstring): supply
    days_to_salary / loans / planned purchase / income_override /
    recurring_overrides / extra_recurring - data the CSV alone can't give us,
    so P3's Purchase-Timing and Arbitrage modules have something to react to."""
    STATE["profile"].update(payload)
    if STATE["result"] is not None:
        transactions = STATE["result"]["transactions"]
        summary = STATE["result"]["summary"]
        STATE["result"]["engine_input"] = build_engine_input(transactions, summary, STATE["profile"])
        _refresh_recommendations()
    return {"profile": STATE["profile"]}
