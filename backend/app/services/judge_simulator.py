from __future__ import annotations
import json
import uuid
from datetime import datetime
from typing import Any

from app.schemas.strategy import JudgeSimulationResponse
from app.services.ai_generator import analyze_with_schema, AIGenerationOptions

async def simulate_judge_perspective(
    strategy_id: str,
    document_text: str,
    context: dict[str, Any] | None = None
) -> JudgeSimulationResponse:
    user_prompt = f"ТЕКСТ ДОКУМЕНТА/СТРАТЕГІЇ ДЛЯ АНАЛІЗУ:\n{document_text}\n\nДОДАТКОВИЙ КОНТЕКСТ:\n{json.dumps(context or {})}"
    
    result = await analyze_with_schema(
        role="judge",
        user_prompt=user_prompt,
        schema=JudgeSimulationResponse,
        options=AIGenerationOptions(temperature=0.7) 
    )
    
    if result.validated_data:
        res: JudgeSimulationResponse = result.validated_data
        res.id = str(uuid.uuid4())
        res.strategy_blueprint_id = strategy_id
        res.created_at = datetime.utcnow().isoformat()
        return res
    
    return JudgeSimulationResponse(
        id=str(uuid.uuid4()),
        strategy_blueprint_id=strategy_id,
        verdict_probability=0.5,
        judge_persona="System Default",
        judge_commentary="Суддя тимчасово не доступний для коментарів.",
        decision_rationale="Помилка генерації аналізу.",
        created_at=datetime.utcnow().isoformat()
    )
