# Financial Health Copilot - fully integrated (P1 + P2 + P3 + P4)

All four people's work, wired together: P1's real CSV categorizer, P2's
real analytics backend, P3's real recommendation engine, and P4's real
dashboard - each kept in its own swappable module. See
`docs/P1_P4_Integration_Notes.md` for what was found wrong in P1/P4 and
exactly how the swap-in/swap-out architecture works.

## Run
```bash
pip install -r requirements.txt
python -m pytest -q                              # 48 tests
uvicorn backend.main:app --reload --port 8000
```
Then open **http://localhost:8000/** for the dashboard (P4), or
**http://localhost:8000/docs** for the interactive API.

## Project layout
```
backend/
  modules/p1/     Person 1: CSV -> categorized transactions
  modules/p2/     Person 2: transactions -> summary analytics
  modules/p3/     Person 3: recommendation engine, What-If, chat
  adapter.py      the P2 -> P3 data seam
  pipeline.py     the one file that wires P1 -> P2 -> P3 together
  main.py         FastAPI app: all endpoints + serves P4 at "/"
frontend/p4/      Person 4: the dashboard (talks to the backend over HTTP only)
sample_data/      shared demo CSV (P1's bank_sample.csv)
tests/            one test file per module + one end-to-end integration file
docs/             implementation guides + integration notes
```

## API
| Endpoint | What it does |
|---|---|
| `POST /upload` | upload a CSV, runs the full P1->P2->P3 chain |
| `POST /load-sample` | one-click demo dataset |
| `GET /summary` | balance, spending, buffer, category chart, top recommendation |
| `GET /transactions` | every cleaned row with category + confidence |
| `GET /forecast` | balance expected before next salary |
| `GET /debt` | debt-to-income, EMIs |
| `GET /commitments` | recurring payments, loans, planned purchase |
| `GET /recommendations` | all 4 modules, ranked and safety-gated |
| `POST /whatif` | `{"cancel": "Netflix"}` -> before/after, real data untouched |
| `POST /chat` | ask a question in plain English; always tagged Fact/Prediction/Recommendation |
| `POST /confirm` | answer a safety-gate "are you sure?" prompt |
| `POST /profile` | add loans / planned purchase / days-to-salary (a CSV alone can't provide these) |

## Quick demo
```bash
curl -X POST http://localhost:8000/load-sample
curl http://localhost:8000/recommendations
curl -X POST http://localhost:8000/profile -H "content-type: application/json" \
     -d '{"loans":[{"name":"Card","emi":2000,"rate":30,"outstanding":50000}],"days_to_salary":10}'
curl -X POST http://localhost:8000/whatif -H "content-type: application/json" -d '{"cancel":"NETFLIX.COM"}'
curl -X POST http://localhost:8000/chat -H "content-type: application/json" -d '{"message":"what should I do?"}'
```
