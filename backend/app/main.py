from __future__ import annotations

from app.app_config import create_app
from app.routers.analyze import router as analyze_router
from app.routers.auto_process import router as auto_process_router
from app.routers.audit import router as audit_router
from app.routers.auth import router as auth_router
from app.routers.billing import router as billing_router
from app.routers.calculate import router as calculate_router
from app.routers.forum import router as forum_router
from app.routers.case_law import router as case_law_router
from app.routers.deadlines import router as deadlines_router
from app.routers.documents import router as documents_router
from app.routers.e_court import router as e_court_router
from app.routers.health import router as health_router
from app.routers.monitoring import router as monitoring_router
from app.routers.notifications import router as notifications_router
from app.routers.opendatabot import router as opendatabot_router
from app.routers.strategy import router as strategy_router
from app.routers.knowledge_base import router as knowledge_base_router
from app.routers.cases import router as cases_router
from app.routers.dashboard import router as dashboard_router

app = create_app()

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(analyze_router)
app.include_router(auto_process_router)
app.include_router(audit_router)
app.include_router(documents_router)
app.include_router(case_law_router)
app.include_router(e_court_router)
app.include_router(monitoring_router)
app.include_router(notifications_router)
app.include_router(calculate_router)
app.include_router(deadlines_router)
app.include_router(billing_router)
app.include_router(strategy_router)
app.include_router(opendatabot_router)
app.include_router(forum_router)
app.include_router(knowledge_base_router)
app.include_router(cases_router)
app.include_router(dashboard_router)
