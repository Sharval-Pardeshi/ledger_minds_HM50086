# Swaroop: Data Pipeline (Stages 1–3)

**Role:** Turn messy uploaded files into clean, trustworthy, confidence-scored transactions.
**Owns:** upload handling, extraction, cleanup, categorization, recurring detection, confidence scoring.

---

## 0. Kickoff (all 4 together, ~45–60 min)
- [ ] Agree on `CleanTransaction` and `Recommendation` JSON shapes → `contracts/`
- [ ] **Your job:** build the shared sample dataset (~200 rows: bank, UPI, CC, loan, MF)
  - Must include: a duplicate, a rent payment, Netflix, a salary, one ambiguous row
  - Output: `sample_data/*.csv` + `sample_clean.json`
- [ ] Agree on endpoint names with P2 + P4 (`contracts/api.md`)

---

## 1. Prototype task
**Goal:** one CSV in → categorized rows out.

| Task | Deliverable |
|---|---|
| Read CSV, categorize with keyword rules, give each row a basic confidence score | `process_csv(file) -> list[CleanTransaction]` |

**Acceptance:** correct categories on the sample data; unmatched rows get **low confidence**.




# Sharval: Backend Core, Database & Analytics (Stage 4 + Infrastructure)

**Role:** The backbone. Supabase, the single backend service, forecasting, debt analysis, deployment, and **integration lead**.

## 1. Prototype task
**Goal:** balance + buffer numbers behind an API.

| Task | Deliverable |
|---|---|
| Compute current balance, average monthly expense, `buffer_months` | `analyze(transactions) -> {balance, avg_expense, buffer_months}` |
| Minimal backend | `/upload` and `/summary` |

**Acceptance:** numbers verified **by hand** against the sample data.

**Integration (last 30–45 min of prototype):** wire P1 → P2 → P3 behind `/upload`; P4 points the frontend at it.

---

