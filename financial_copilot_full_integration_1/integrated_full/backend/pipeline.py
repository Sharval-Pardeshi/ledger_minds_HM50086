"""
pipeline.py - chains all 4 people's work: P1 -> P2 -> (adapter) -> P3.

THIS FILE IS DELIBERATELY THE ONLY PLACE THAT WIRES MODULES TOGETHER.
Each import below is one swap point. To update/replace a person's part:
    1. Remove/replace their folder under backend/modules/<p1|p2|p3>/
       (keeping the same public function name(s) - see that module's
       __init__.py for the exact contract expected).
    2. If their public function name or signature changed, update ONLY
       the matching import line below.
    3. Nothing else in the app needs to change.
P4 is not imported here at all - it only ever talks to this backend over
the HTTP endpoints in main.py, so it is swappable independently too
(see frontend/p4/README.md).
"""
from .adapter import build_engine_input                 # <- P2 -> P3 seam (this repo's glue, not a person's module)
from .modules.p1 import process_csv_text                # <- SWAP POINT: Person 1's pipeline
from .modules.p2 import analyze                          # <- SWAP POINT: Person 2's analytics
from .modules.p3 import all_recommendations, gate         # <- SWAP POINT: Person 3's engine


def run_prototype_pipeline(csv_text: str, opening_balance: float = 0.0, profile: dict | None = None) -> dict:
    """CSV text in -> everything the dashboard, chat and what-if need out."""
    transactions = process_csv_text(csv_text)                       # P1
    summary = analyze(transactions, opening_balance)                 # P2
    engine_input = build_engine_input(transactions, summary, profile)  # P2 -> P3 seam
    recommendations = gate(all_recommendations(engine_input))        # P3
    return {
        "transactions": transactions,
        "summary": summary,
        "engine_input": engine_input,
        "recommendations": recommendations,
        # Backward-compatible single top pick (same shape as the old P3 stub).
        "recommendation": recommendations[0] if recommendations else None,
    }
