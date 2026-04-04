import sys
print("starting analyze trace")
try:
    print("importing fastapi")
    from fastapi import APIRouter
    print("importing sqlalchemy")
    from sqlalchemy.orm import Session
    print("importing app.auth")
    from app.auth import CurrentUser, get_current_user
    print("importing app.database")
    from app.database import get_db
    print("importing app.schemas")
    from app.schemas import AnalyzeProcessRequest, ContractAnalysisHistoryResponse, ContractAnalysisItem
    print("importing app.services.audit")
    from app.services.audit import log_action
    print("importing app.services.contract_analyses")
    from app.services.contract_analyses import analyze_contract_text
    print("importing app.services.subscriptions")
    from app.services.subscriptions import ensure_analysis_quota
    print("done analyzing imports")
except Exception as e:
    print(f"error: {e}")
