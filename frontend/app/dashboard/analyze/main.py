"""
FastAPI application entry point.

Registers all routers under their respective prefixes.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Legal AI Platform API",
    version="1.0.0",
    description="Backend API for AI-powered Ukrainian legal document analysis and generation.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Router registration
# ---------------------------------------------------------------------------

from app.auth import router as auth_router
from .cases import router as cases_router
from .gdpr import router as gdpr_router
from .intake import router as intake_router
from .document_signed_url import router as signed_url_router
from .user_preferences import router as prefs_router
from .batch import router as batch_router
from .comments import router as comments_router
from .processual_gates import router as processual_gates_router  # STORY-0B
from .export_gates import router as export_gates_router          # STORY-0C
from .document_export import router as document_export_router    # STORY-7/8

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(cases_router, prefix="/api/cases", tags=["cases"])
app.include_router(gdpr_router, prefix="/api/analyze", tags=["gdpr"])
app.include_router(intake_router, prefix="/api/analyze", tags=["intake"])
app.include_router(batch_router, prefix="/api/analyze", tags=["intake"])
app.include_router(comments_router, prefix="/api/analyze", tags=["comments"])
app.include_router(signed_url_router, prefix="/api/documents", tags=["documents"])
app.include_router(processual_gates_router, prefix="/api/documents", tags=["processual-gates"])
app.include_router(export_gates_router, prefix="/api/documents", tags=["export-gates"])
app.include_router(document_export_router, prefix="/api/documents", tags=["export"])  # STORY-7/8
app.include_router(prefs_router, prefix="/api/users", tags=["users"])
