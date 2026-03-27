"""
Package init for the analyze backend stubs.

Re-exports the public schema contracts so any router can import with:

    from app.dashboard.analyze import AnalyzeBatchProcessRequest

The separate backend must replicate these exports in its own
app/schemas/__init__.py (see schemas.py for the Pydantic definitions).
"""

from .schemas import (
    AnalyzeBatchProcessRequest,
    AnalyzeBatchProcessResponse,
    AnalyzeBatchProcessResponseItem,
    AnalyzeIntakeRequest,
)

__all__ = [
    "AnalyzeIntakeRequest",
    "AnalyzeBatchProcessRequest",
    "AnalyzeBatchProcessResponse",
    "AnalyzeBatchProcessResponseItem",
]
