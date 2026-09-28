"""
backend/modules/p2/__init__.py - Person 2's module boundary.

Public surface: `analyze(transactions, opening_balance) -> summary dict`
(Doc 02's P2 prototype deliverable). To swap in a new P2 module, replace
analytics.py with the same `analyze()` signature and output contract - the
rest of the app (pipeline.py) only ever imports from here.
"""
from .analytics import analyze

__all__ = ["analyze"]
