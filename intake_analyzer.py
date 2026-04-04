from __future__ import annotations

import json
from fastapi import UploadFile, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.db import get_session
from app.models.generated_document import GeneratedDocument # Припускаємо, що ця модель існує
from app.services.ai_generator import generate_legal_document
from app.services.auto_processor import build_document_fact_pack, build_form_data_for_doc_type, suggest_document_types
from app.services.auto_processor import _repair_mojibake_text

async def run_intake_analysis(
    file: UploadFile,
    user_id: str,
    mode: str = "standard",
    jurisdiction: str = "UA",
    case_id: str | None = None,
    session: AsyncSession = Depends(get_session)
) -> dict:
    """
    Performs intake analysis on an uploaded document, classifies it,
    and can link it to a case.
    """
    file_content = await file.read()
    text_content = file_content.decode("utf-8", errors="ignore")
    
    # Basic text cleaning and mojibake repair
    cleaned_text = _repair_mojibake_text(text_content)

    # Stage 1: Document Classification (using AI_GENERATION_PROMPTS_CATALOG.md logic)
    # For brevity, I'll use a simplified version here. In a real scenario,
    # you'd load the full prompt from a catalog or config.
    system_prompt_classifier = (
        "You are an elite Ukrainian legal AI with 25+ years of experience. "
        "Your task: Analyze the provided legal document and classify it with surgical precision. "
        "Output ONLY valid JSON. No markdown, no explanations, no preamble. "
        "Identify document_type, jurisdiction, primary_party_role, subject_matter, "
        "financial_exposure, urgency_level, risk_levels (legal, procedural, financial), "
        "detected_issues, and a preliminary_assessment (recommendation, next_steps, confidence)."
        "All text content (except enum values) should be in Ukrainian."
    )
    user_prompt_classifier = f"Проаналізуй наступний документ:\n\n---\n{cleaned_text[:15000]}"
    
    classification_result_ai = await generate_legal_document(
        system_prompt_classifier, user_prompt_classifier, session_id=f"user:{user_id}"
    )
    
    if not classification_result_ai.used_ai or not classification_result_ai.text:
        raise ValueError("AI service failed to classify the document.")

    try:
        classification_data = json.loads(classification_result_ai.text)
    except json.JSONDecodeError:
        raise ValueError(f"AI returned invalid JSON for classification: {classification_result_ai.text}")

    # Fallback/refinement for doc_type if AI is unsure or returns unknown
    doc_type = classification_data.get("classified_type")
    if not doc_type or doc_type not in suggest_document_types(cleaned_text, max_documents=1): # Simplified check
        doc_type = suggest_document_types(cleaned_text, max_documents=1)[0]
        classification_data["classified_type"] = doc_type

    # Build form_data for potential document generation
    form_data = build_form_data_for_doc_type(doc_type, cleaned_text)

    # Save the analysis result as a GeneratedDocument (or similar)
    # This assumes a GeneratedDocument model exists and has a case_id field
    new_document = GeneratedDocument(
        user_id=user_id,
        document_type=doc_type,
        document_category=classification_data.get("subject_matter", "general"),
        title=classification_data.get("preliminary_assessment", {}).get("recommendation", file.filename),
        generated_text=cleaned_text, # Store raw text for now, or a summary
        preview_text=cleaned_text[:1000],
        form_data=form_data,
        ai_model=classification_result_ai.model,
        tokens_used=classification_result_ai.tokens_used,
        ai_error=classification_result_ai.error,
        case_id=UUID(case_id) if case_id else None,
        # Add other fields from classification_data as needed
        classified_type=classification_data.get("classified_type"),
        jurisdiction=classification_data.get("jurisdiction"),
        primary_party_role=classification_data.get("primary_party_role"),
        subject_matter=classification_data.get("subject_matter"),
        financial_exposure_amount=classification_data.get("financial_exposure", {}).get("amount"),
        urgency_level=classification_data.get("urgency_level"),
        risk_level_legal=classification_data.get("risk_levels", {}).get("legal"),
        risk_level_procedural=classification_data.get("risk_levels", {}).get("procedural"),
        risk_level_financial=classification_data.get("risk_levels", {}).get("financial"),
        detected_issues=classification_data.get("detected_issues", []),
        classifier_confidence=classification_data.get("preliminary_assessment", {}).get("classification_confidence"),
        raw_text_preview=cleaned_text[:2000],
    )
    session.add(new_document)
    await session.commit()
    await session.refresh(new_document)

    return {**classification_data, "id": str(new_document.id)}
