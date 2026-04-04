from __future__ import annotations
from app.services.ai_generator import generate_legal_document
import re

async def analyze_gdpr_compliance(text: str, *, session_id: str | None = None) -> dict:
    """
    Analyzes text for GDPR compliance issues.
    """
    system_prompt = (
        "You are a certified GDPR and data privacy expert. Your task is to analyze the provided text "
        "for potential GDPR compliance issues. Focus on personal data processing, consent, data subject rights, "
        "and international data transfers. Provide a concise report in Ukrainian using Markdown."
    )
    user_prompt = (
        "Проаналізуй наступний текст на відповідність GDPR. "
        "Вияви потенційні проблеми, пов'язані з персональними даними, згодою, правами суб'єктів даних. "
        "Сформуй короткий звіт у форматі Markdown.\n\n"
        f"ТЕКСТ ДЛЯ АНАЛІЗУ:\n---\n{text[:8000]}"
    )
    
    result = await generate_legal_document(system_prompt, user_prompt, session_id=session_id)
    
    if not result.used_ai:
        raise ValueError("AI service failed to generate GDPR report.")

    # A simple way to count issues for the response model
    issues_found = len(re.findall(r"[\*•-]\s|\d\.\s", result.text))
    
    return {
        "report": result.text,
        "issues_found": issues_found
    }