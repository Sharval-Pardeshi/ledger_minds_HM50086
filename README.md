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
