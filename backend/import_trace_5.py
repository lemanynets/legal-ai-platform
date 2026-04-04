import sys
import traceback

with open("trace.txt", "w") as f:
    f.write("starting analyze trace\n")

def log(msg):
    with open("trace.txt", "a") as f:
        f.write(msg + "\n")

try:
    log("importing fastapi")
    from fastapi import APIRouter
    log("importing sqlalchemy")
    from sqlalchemy.orm import Session
    log("importing app.auth")
    from app.auth import CurrentUser, get_current_user
    log("importing app.database")
    from app.database import get_db
    log("importing app.schemas")
    from app.schemas import AnalyzeProcessRequest, ContractAnalysisHistoryResponse, ContractAnalysisItem
    log("importing app.services.audit")
    from app.services.audit import log_action
    log("importing app.services.contract_analyses")
    from app.services.contract_analyses import analyze_contract_text
    log("importing app.services.subscriptions")
    from app.services.subscriptions import ensure_analysis_quota
    log("done analyzing imports")
except Exception as e:
    log(f"error: {str(e)}")
