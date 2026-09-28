"""
Generates the PROTOTYPE sample CSV: a single bank statement, 2 months,
matching the format from Doc 01 workflow step 1: date, description, amount, type.

This is a SUBSET of the persona (Rohan) used for the full Hackathon Final
multi-source dataset later. Kept small and single-source on purpose, since
the prototype only needs one CSV to demo the thin end-to-end slice.

Deliberate trap rows included (per Hour-1 kickoff spec):
  - a duplicate row        (row 14 and row 15 are identical)
  - a rent payment         (recurring, unlabeled-ish description)
  - a Netflix subscription (recurring, clean merchant name)
  - a salary credit        (income, twice -> once per month)
  - an ambiguous row       (personal UPI transfer, no clear category)
"""
import csv
from pathlib import Path

rows = [
    # (date, description, amount, type)
    ("2026-05-01", "SALARY CREDIT - TECHCORP PVT LTD", 62000.00, "credit"),
    ("2026-05-03", "UPI/408213445/RAJESH KUMAR/RENT MAY", 14000.00, "debit"),
    ("2026-05-05", "EDU LOAN EMI AUTO DEBIT", 8500.00, "debit"),
    ("2026-05-06", "NETFLIX.COM", 649.00, "debit"),
    ("2026-05-07", "SIP - INDEX FUND MF", 5000.00, "debit"),
    ("2026-05-08", "UPI/SWIGGY*ORDER/BUNDL TECH", 420.00, "debit"),
    ("2026-05-09", "BIGBASKET GROCERY", 2100.00, "debit"),
    ("2026-05-10", "UPI/OLA CABS", 260.00, "debit"),
    ("2026-05-11", "ELECTRICITY BILL BSES", 1350.00, "debit"),
    ("2026-05-12", "AMAZON.IN", 1899.00, "debit"),
    ("2026-05-13", "AIRTEL POSTPAID", 499.00, "debit"),
    ("2026-05-14", "UPI/SWIGGY*ORDER/BUNDL TECH", 380.00, "debit"),
    ("2026-05-15", "CREDIT CARD BILL PAYMENT", 6200.00, "debit"),
    ("2026-05-16", "UPI/9988776655/RAKESH", 1500.00, "debit"),   # <- duplicate #1
    ("2026-05-16", "UPI/9988776655/RAKESH", 1500.00, "debit"),   # <- duplicate #2 (same row again)
    ("2026-05-18", "ZOMATO ONLINE ORDER", 350.00, "debit"),
    ("2026-05-19", "HPCL PETROL PUMP", 1200.00, "debit"),
    ("2026-05-20", "DMART RETAIL", 1650.00, "debit"),
    ("2026-05-21", "ATM WITHDRAWAL", 3000.00, "debit"),
    ("2026-05-22", "SPOTIFY PREMIUM", 119.00, "debit"),
    ("2026-05-24", "UPI/AMAZON/GENERIC PURCHASE", 2400.00, "debit"),  # ambiguous: shopping or groceries?
    ("2026-05-27", "APOLLO PHARMACY", 540.00, "debit"),
    ("2026-05-29", "UPI/FRIEND SPLIT DINNER/VIKAS", 600.00, "debit"),  # ambiguous: personal transfer
    ("2026-06-01", "SALARY CREDIT - TECHCORP PVT LTD", 62000.00, "credit"),
    ("2026-06-03", "UPI/408213445/RAJESH KUMAR/RENT JUNE", 14000.00, "debit"),
    ("2026-06-05", "EDU LOAN EMI AUTO DEBIT", 8500.00, "debit"),
    ("2026-06-06", "NETFLIX.COM", 649.00, "debit"),
    ("2026-06-07", "SIP - INDEX FUND MF", 5000.00, "debit"),
    ("2026-06-08", "UPI/SWIGGY*ORDER/BUNDL TECH", 460.00, "debit"),
    ("2026-06-09", "BIGBASKET GROCERY", 2350.00, "debit"),
    ("2026-06-10", "UPI/UBER TRIP", 210.00, "debit"),
    ("2026-06-11", "ELECTRICITY BILL BSES", 1780.00, "debit"),
    ("2026-06-13", "AIRTEL POSTPAID", 499.00, "debit"),
    ("2026-06-15", "CREDIT CARD BILL PAYMENT", 5400.00, "debit"),
    ("2026-06-17", "FLIPKART ONLINE", 3200.00, "debit"),
    ("2026-06-19", "HPCL PETROL PUMP", 1100.00, "debit"),
    ("2026-06-21", "UPI/RANDOM MERCHANT XYZ", 890.00, "debit"),  # ambiguous: unknown merchant
    ("2026-06-23", "SPOTIFY PREMIUM", 119.00, "debit"),
    ("2026-06-25", "DMART RETAIL", 1420.00, "debit"),
    ("2026-06-28", "APOLLO PHARMACY", 320.00, "debit"),
]

out_path = Path(__file__).parent / "sample_data" / "bank_sample.csv"
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["date", "description", "amount", "type"])
    writer.writerows(rows)

print(f"Wrote {len(rows)} rows to {out_path}")
