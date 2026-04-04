from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Any

from app.services.auth import get_current_user
from app.services.auto_processor import generate_document_packet_from_strategy
from app.services.judge_simulator import simulate_judge_verdict
from app.models.user import User

router = APIRouter()


class StrategyTextRequest(BaseModel):
    strategy_text: str


class GeneratedDocumentPacketItem(BaseModel):
    doc_type: str
    title: str
    generated_text: str
    ai_model: str | None
    tokens_used: int | None
    ai_error: str | None
    _source_form_data: dict[str, Any]


class JudgeSimulationResponse(BaseModel):
    win_probability: float
    vulnerabilities: list[str]
    recommendations: list[str]
    judge_commentary: str


@router.post(
    "/strategy/simulate-judge",
    response_model=JudgeSimulationResponse,
    summary="Simulate a judge's verdict on a strategy",
)
async def simulate_judge_endpoint(
    request: StrategyTextRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Takes a markdown strategy blueprint and simulates a judge's feedback,
    including win probability, vulnerabilities, and recommendations.
    """
    try:
        session_id = f"user:{current_user.id}"
        verdict = await simulate_judge_verdict(request.strategy_text, session_id=session_id)
        return verdict
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="An unexpected error occurred during judge simulation.")


@router.post(
    "/strategy/generate-packet",
    response_model=list[GeneratedDocumentPacketItem],
    summary="Generate a packet of documents from a strategy blueprint",
)
async def generate_packet_from_strategy_endpoint(
    request: StrategyTextRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Takes a markdown strategy blueprint and uses an AI to parse it and generate
    a corresponding packet of procedural documents.
    """
    try:
        session_id = f"user:{current_user.id}"
        generated_docs = await generate_document_packet_from_strategy(
            strategy_text=request.strategy_text, session_id=session_id
        )
        return generated_docs
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="An unexpected error occurred during document packet generation.")