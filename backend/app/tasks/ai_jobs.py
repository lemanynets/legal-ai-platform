from __future__ import annotations

import base64
import json
import os
from datetime import datetime
from typing import Any

from app.core.celery_app import celery_app


_DOC_LABELS = {
    "pozov_do_sudu": "Позов до суду",
    "pozov_trudovyi": "Трудовий позов",
    "appeal_complaint": "Апеляційна скарга",
    "dohovir_kupivli_prodazhu": "Договір купівлі-продажу",
    "dohovir_orendi": "Договір оренди",
    "dohovir_nadannia_posluh": "Договір про надання послуг",
    "pretenziya": "Претензія",
    "dovirennist": "Довіреність",
}


def _template_document(doc_type: str, form_data: dict[str, Any]) -> str:
    label = _DOC_LABELS.get(doc_type, doc_type)
    lines = [label.upper(), "", "Реквізити:"]
    for key, value in form_data.items():
        if value:
            lines.append(f"- {key}: {value}")
    lines.append("\n(Згенеровано шаблоном)\n")
    return "\n".join(lines)


def _run_generation(doc_type: str, form_data: dict[str, Any], extra_context: str | None = None) -> dict[str, Any]:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        text = _template_document(doc_type, form_data)
        return {
            "document_type": doc_type,
            "title": _DOC_LABELS.get(doc_type, doc_type),
            "generated_text": text,
            "preview_text": text[:200],
            "ai_model": "template-fallback",
            "used_ai": False,
        }
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        fields_text = "\n".join(f"  {k}: {v}" for k, v in form_data.items() if v)
        extra = f"\n\nДодатковий контекст: {extra_context}" if extra_context else ""
        prompt = (
            f"Ти — досвідчений юрист. Склади юридичний документ: {_DOC_LABELS.get(doc_type, doc_type)}.\n\n"
            f"Дані для документа:\n{fields_text}{extra}\n\n"
            "Вимоги: формальний стиль, українська мова, готовий до подання."
        )
        message = client.messages.create(
            model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        text = message.content[0].text
        return {
            "document_type": doc_type,
            "title": _DOC_LABELS.get(doc_type, doc_type),
            "generated_text": text,
            "preview_text": text[:200],
            "ai_model": os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
            "used_ai": True,
        }
    except Exception:
        text = _template_document(doc_type, form_data)
        return {
            "document_type": doc_type,
            "title": _DOC_LABELS.get(doc_type, doc_type),
            "generated_text": text,
            "preview_text": text[:200],
            "ai_model": "template-fallback",
            "used_ai": False,
        }


def _run_intake_analysis(file_b64: str, file_name: str, jurisdiction: str, mode: str) -> dict[str, Any]:
    try:
        raw = base64.b64decode(file_b64.encode("utf-8"))
    except Exception:
        raw = b""
    preview = raw.decode("utf-8", errors="replace")[:500]
    tags = ["async", mode]
    return {
        "source_file_name": file_name,
        "classified_type": "unknown",
        "document_language": "uk",
        "jurisdiction": jurisdiction,
        "subject_matter": "Асинхронний intake аналіз",
        "urgency_level": "medium",
        "risk_level_legal": "medium",
        "risk_level_procedural": "low",
        "risk_level_financial": "low",
        "detected_issues": [],
        "raw_text_preview": preview,
        "tags": tags,
        "processed_at": datetime.utcnow().isoformat(),
    }


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=2, retry_jitter=True)
def generate_document_job(self, doc_type: str, form_data: dict[str, Any], extra_context: str | None = None) -> dict[str, Any]:
    self.update_state(state="PROGRESS", meta={"progress": 15, "message": "Підготовка даних"})
    result = _run_generation(doc_type, form_data, extra_context)
    self.update_state(state="PROGRESS", meta={"progress": 90, "message": "Формування результату"})
    return result


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=2, retry_jitter=True)
def analyze_intake_job(self, payload: dict[str, Any]) -> dict[str, Any]:
    self.update_state(state="PROGRESS", meta={"progress": 20, "message": "Зчитування файлу"})
    result = _run_intake_analysis(
        payload.get("file_b64", ""),
        payload.get("file_name", "document"),
        payload.get("jurisdiction", "UA"),
        payload.get("mode", "standard"),
    )
    self.update_state(state="PROGRESS", meta={"progress": 90, "message": "Аналіз завершено"})
    return result
