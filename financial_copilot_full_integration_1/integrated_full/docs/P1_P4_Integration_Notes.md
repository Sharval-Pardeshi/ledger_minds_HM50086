# P1 + P4 Integration Notes

This picks up where `P3_Integration_Notes.md` (P2+P3) left off. It covers
two things: whether `p1.zip` and `p4.html` meet the prototype's conditions,
and how all 4 people's work is now wired together so any one part can be
pulled out, changed, and put back without touching the others.

## 1. Does P1 fulfill the prototype conditions?

**Yes, with two real bugs found and one packaging issue fixed.**

`process_csv.py` does what Doc 01/02 ask of P1: reads a CSV, assigns a
category and a confidence score per row via keyword rules, and outputs
valid `CleanTransaction` objects (every required field present, correct
`direction` values, ISO dates) - confirmed by running it through P2's own
`validate_transactions()` contract check with zero errors. The 40-row
sample dataset deliberately includes a duplicate row, ambiguous merchants,
and unrecognizable ones, matching Doc 02's kickoff-dataset spec.

Two things were **not** fully correct, found by actually running it rather
than reading it:

1. **Packaging bug.** `process_csv.py`'s own `__main__` block, its test file,
   and its README all expect `sample_data/bank_sample.csv`, but the zip
   shipped the CSV flat at the root next to the script. Fixed by giving it
   the `sample_data/` folder it already expects
   (`backend/modules/p1/sample_data/`).
2. **Keyword substring bug.** The `"Loan/EMI"` rule matches if `"emi"`
   appears *anywhere* in the description - which means `"SPOTIFY PREMIUM"`
   (contains "pr**emi**um") gets categorized as `Loan/EMI` instead of
   `Subscriptions`. This is a real bug in P1's rule matching (needs a
   word-boundary check, e.g. a regex like `\bemi\b`), not something fixed
   here - it's left in P1's own file so P1 stays a clean, swappable module,
   but it's flagged here so the team knows before the demo.
3. **No column validation.** Unlike the old placeholder P2 used to test
   against, the real `process_csv()` assumes `date`/`description`/`amount`/
   `type` columns exist and throws a bare `KeyError` if one is missing,
   instead of a clean message. This *is* handled, but at the integration
   boundary (`backend/main.py`'s `_process()` catches it and returns a
   proper `400` with a clear message) rather than inside P1's file, for the
   same swappability reason.

## 2. Does P4 fulfill the prototype conditions?

**Partially, as delivered.** The visual design, layout, and - importantly -
the *shape* of its internal mock data (`STATE`: balance, income,
days_to_salary, recurring[], loans[], planned) already matches P3's real
engine input almost exactly, which made wiring it up straightforward. But
as received, `p4.html` made **zero network calls**: the upload button just
showed an alert and never read the file, the chat box matched user text
against hard-coded regexes and printed canned strings, and every number on
the dashboard came from one hard-coded JS object. Doc 02's own plan for P4
was "build against a mock JSON first, then switch to the real API with a
small change" - the mock-building half was done well; the switch had not
happened yet.

**What was changed:** all the CSS and HTML markup is untouched. The
`<script>` block was rewritten to fetch from the real backend instead of
reading the local `STATE` object:

| Dashboard element | Now reads from |
|---|---|
| Balance, spending, buffer tiles | `GET /summary` |
| Category chart | `GET /summary` (`category_breakdown`) |
| Uncertain-transaction alert | `GET /transactions` (first `Uncertain` row, hidden if none) |
| Recurring / loans / planned panel | `GET /commitments` |
| Top recommendation card | `GET /summary` (`recommendation`) |
| Upload button | `POST /upload` (real `FormData`, not a fake alert) |
| "Load sample" button | `POST /load-sample` |
| Chat - facts/predictions/advice | `POST /chat` |
| Chat - "what if I cancel X" | `POST /whatif` (real before/after, not guessed) |

## 3. The full architecture: how to swap any one of P1-P4

```
backend/
  modules/
    p1/            <- Person 1's module. Public surface: modules/p1/__init__.py
    p2/            <- Person 2's module. Public surface: modules/p2/__init__.py
    p3/            <- Person 3's module. Public surface: modules/p3/__init__.py
  adapter.py       <- the P2->P3 seam (not owned by one person; project glue)
  pipeline.py      <- the ONLY file that imports all three modules together
  main.py          <- FastAPI app: endpoints + serves P4 at "/"
frontend/
  p4/index.html    <- Person 4's module. Talks to the backend only over HTTP.
```

**The rule:** nothing outside a module folder ever reaches inside it. Every
other file talks to a module only through the handful of functions listed
in that module's own `__init__.py`. `pipeline.py` is the single place all
three backend modules are imported together, and each import line is
commented as a swap point.

**To update or replace someone's part:**

1. **P1** - replace the contents of `backend/modules/p1/` (keep a
   `process_csv(file_path) -> list[CleanTransaction]` function, or update
   the one-line wrapper in `modules/p1/__init__.py` if the signature
   changes). Nothing in `pipeline.py`, `main.py`, P2, or P3 needs to know.
2. **P2** - replace `backend/modules/p2/analytics.py`, keeping
   `analyze(transactions, opening_balance) -> summary` and the same output
   contract (`backend/contracts.py`). `adapter.py` and P3 are untouched.
3. **P3** - replace `backend/modules/p3/engine.py`, keeping the function
   names `all_recommendations`, `gate`, `whatif`, `chat`, `recompute`. If
   the *input shape* P3 expects changes, only `adapter.py` needs an update
   - P1 and P2 are untouched.
4. **P4** - replace `frontend/p4/index.html` (or point it at a different
   `API_BASE`) with anything that speaks the same 9 HTTP endpoints listed
   in the main `README.md`. The backend has no idea what's rendering it.

Run `python -m pytest -q` after any swap - `tests/test_p1_module.py`,
`test_analytics.py`, and `test_engine.py` each test one module in
isolation, and `test_integration.py` tests the whole chain, so a break in
any one person's part fails a specific, obviously-named test file.
