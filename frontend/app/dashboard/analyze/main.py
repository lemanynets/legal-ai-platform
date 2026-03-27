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

from .cases import router as cases_router
from .gdpr import router as gdpr_router
from .intake import router as intake_router
from .document_signed_url import router as signed_url_router

app.include_router(cases_router, prefix="/api/cases", tags=["cases"])
app.include_router(gdpr_router, prefix="/api/analyze", tags=["gdpr"])
app.include_router(intake_router, prefix="/api/analyze", tags=["intake"])
app.include_router(signed_url_router, prefix="/api/documents", tags=["documents"])
