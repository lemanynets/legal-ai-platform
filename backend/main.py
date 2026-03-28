"""
Backend entry point.

Mounts the co-located FastAPI app from frontend/app/dashboard/analyze/main.py.
PYTHONPATH must include both backend/ and frontend/ so that:
  - `from app.db import ...`  → resolves to backend/app/db.py
  - `from .cases import ...`  → resolves within analyze/ package
"""
import sys
import os

# Ensure backend/ and frontend/ are both on sys.path
_here = os.path.dirname(__file__)
_frontend = os.path.join(_here, "..", "frontend")

for _p in [_here, _frontend]:
    _ap = os.path.abspath(_p)
    if _ap not in sys.path:
        sys.path.insert(0, _ap)

# Import the FastAPI app from the analyze package
from app.dashboard.analyze.main import app  # noqa: E402

if __name__ == "__main__":
    import uvicorn  # noqa: PLC0415

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("RELOAD", "false").lower() == "true",
    )
