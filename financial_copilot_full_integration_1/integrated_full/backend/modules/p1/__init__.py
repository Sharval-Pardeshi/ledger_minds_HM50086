"""
backend/modules/p1/__init__.py - Person 1's module boundary.

This is the ONE file the rest of the app imports from. It re-exports P1's
real, unmodified `process_csv.py` (copied in as-is from p1.zip) and adds a
single adapter function, `process_csv_text()`, because P1's real function
signature is `process_csv(file_path: str)` (it opens the file itself) while
the backend receives an uploaded CSV as in-memory text.

WHY THIS MATTERS FOR SWAPPING P1 LATER:
    pipeline.py never calls process_csv() directly - it only calls
    `process_csv_text()` from this file. So replacing P1's work is:
        1. Drop the new process_csv.py in this folder (same public
           function name and CleanTransaction[] output contract).
        2. Update the one-line wrapper below if their signature differs.
        3. Nothing else in the app changes.
"""
import tempfile
from pathlib import Path

from .process_csv import categorize, confidence_label, process_csv  # noqa: F401 (re-exported)

__all__ = ["process_csv", "process_csv_text", "categorize", "confidence_label"]


def process_csv_text(csv_text: str) -> list[dict]:
    """CSV file *content* in -> list[CleanTransaction] out.

    Writes to a throwaway temp file because P1's real `process_csv()` takes
    a file path, not text. Swap-safe: if a future P1 module accepts text
    directly, this becomes a one-line pass-through.
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="") as tmp:
        tmp.write(csv_text)
        tmp_path = Path(tmp.name)
    try:
        return process_csv(str(tmp_path))
    finally:
        tmp_path.unlink(missing_ok=True)
