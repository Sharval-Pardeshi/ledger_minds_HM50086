"""
backend/modules/p3/__init__.py - Person 3's module boundary.

Public surface: the recommendation engine (`all_recommendations`, `gate`,
`whatif`, `chat`, `recompute`, `rank`) ported from p3_test_lab_prototype.html.
To swap in a new P3 module, keep these same function names/signatures - the
rest of the app (pipeline.py, main.py) only ever imports from here.
"""
from .engine import (
    all_recommendations, chat, combine_confidence, gate, mask, rank,
    rec_arbitrage, rec_buffer, rec_purchase_timing, rec_subscriptions,
    recompute, whatif,
)

__all__ = [
    "all_recommendations", "chat", "combine_confidence", "gate", "mask",
    "rank", "rec_arbitrage", "rec_buffer", "rec_purchase_timing",
    "rec_subscriptions", "recompute", "whatif",
]
