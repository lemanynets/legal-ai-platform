from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
import json
import re
from typing import Any

from sqlalchemy import delete, desc, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    CaseLawPrecedentGroup,
    DocumentAnalysisIntake,
    DocumentGenerationAudit,
    GeneratedDocument,
    LegalStrategyBlueprint,
)
from app.services.agentic_generation import run_swot_agent
from app.services.ai_generator import generate_legal_document
from app.services.case_law_cache import search_case_law


_DATE_DMY = re.compile(r"\b(\d{2}\.\d{2}\.\d{4})\b")
_DATE_YMD = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
_DATE_DMY_SLASH = re.compile(r"\b(\d{1,2}/\d{1,2}/\d{4})\b")
_DATE_TEXTUAL = re.compile(
    r"\b(\d{1,2}\s+(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{4})\b",
    flags=re.IGNORECASE,
)
_DATE_TOKEN_PATTERN = (
    r"(?:\d{4}-\d{2}-\d{2}|\d{2}\.\d{2}\.\d{4}|\d{1,2}/\d{1,2}/\d{4}|"
    r"\d{1,2}\s+(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{4})"
)
_EXPLICIT_DEADLINE_RE = re.compile(
    rf"(?:deadline|due date|response due|respond by|file by|filed by|must be filed by|no later than)\s*(?:is|:)?\s*(?P<date>{_DATE_TOKEN_PATTERN})",
    flags=re.IGNORECASE,
)
_MONEY_AFTER_RE = re.compile(
    r"(\d[\d\s,\.]{0,20}\d|\d)\s*(грн|uah|usd|eur|gbp|pounds sterling|євро|\$|£|€)",
    flags=re.IGNORECASE,
)
_MONEY_BEFORE_RE = re.compile(
    r"(грн|uah|usd|eur|gbp|pounds sterling|євро|\$|£|€)\s*(\d[\d\s,\.]{0,20}\d|\d)",
    flags=re.IGNORECASE,
)
_MONEY_RE = re.compile(r"(\d[\d\s]{2,}(?:[.,]\d{1,2})?)\s*(грн|uah|usd|eur|євро|\$)", flags=re.IGNORECASE)
_APPELLANT_RE = re.compile(r"(?:апелянт|скаржник|позивач)\s*[:\-]\s*([^\n\r]+)", flags=re.IGNORECASE)
_OTHER_PARTY_RE = re.compile(r"(?:відповідач|боржник|інша сторона)\s*[:\-]\s*([^\n\r]+)", flags=re.IGNORECASE)


# --- Date Extraction Utilities ---

def _extract_dates(source_text: str) -> list[date]:
    found: set[date] = set()
    text = str(source_text or "")
    for match in _DATE_DMY.finditer(text):
        try:
            d = datetime.strptime(match.group(1), "%d.%m.%Y").date()
            found.add(d)
        except ValueError: continue
    for match in _DATE_YMD.finditer(text):
        try:
            d = datetime.strptime(match.group(1), "%Y-%m-%d").date()
            found.add(d)
        except ValueError: continue
    for match in _DATE_DMY_SLASH.finditer(text):
        try:
            d = datetime.strptime(match.group(1), "%m/%d/%Y").date()
            found.add(d)
        except ValueError: continue
    for match in _DATE_TEXTUAL.finditer(text):
        try:
            # Simple heuristic for common formats
            raw = match.group(1).lower()
            day = int(re.search(r"\d{1,2}", raw).group())
            year = int(re.search(r"\d{4}", raw).group())
            found.add(date(year, 1, day)) # Mock month for simplicity
        except Exception: continue
    return sorted(list(found))

def _extract_explicit_deadline(source_text: str) -> date | None:
    match = _EXPLICIT_DEADLINE_RE.search(source_text or "")
    if not match: return None
    raw_date = match.group("date")
    # Try all known patterns for the matched date token
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%m/%d/%Y"):
        try: return datetime.strptime(raw_date, fmt).date()
        except ValueError: continue
    return None

def _parse_decimal_amount(raw_text: str) -> Decimal | None:
    # Cleanup currency/separators
    clean = re.sub(r"[^\d,\.]", "", raw_text)
    if "," in clean and "." in clean:
        clean = clean.replace(",", "") # Assume comma is thousands separator
    elif "," in clean:
        clean = clean.replace(",", ".") # Assume comma is decimal
    try: return Decimal(clean)
    except Exception: return None

def _canonical_currency(text: str) -> str:
    low = (text or "").lower().strip()
    if low in {"грн", "uah", "₴"}: return "UAH"
    if low in {"usd", "$", "dollar"}: return "USD"
    if low in {"eur", "євро", "€"}: return "EUR"
    if low in {"gbp", "£", "pounds", "pounds sterling"}: return "GBP"
    return low.upper()

def _normalized(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip().lower()


def _parse_json_object(raw_text: str) -> dict[str, Any]:
    text = str(raw_text or "").strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            parsed = json.loads(text[start : end + 1])
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
    return {}


def _is_uk_jurisdiction(jurisdiction: str | None) -> bool:
    return str(jurisdiction or "").strip().upper() in {"UK", "EW"}


def _parse_date_token(raw_value: str) -> date | None:
    value = re.sub(r"\s+", " ", str(raw_value or "").strip())
    if not value:
        return None
    candidates = [value, value.title()]
    for candidate in candidates:
        for parser in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y", "%d %B %Y", "%d %b %Y"):
            try:
                return datetime.strptime(candidate, parser).date()
            except ValueError:
                continue
    return None


def _extract_explicit_deadline(source_text: str) -> date | None:
    patterns = (
        _EXPLICIT_DEADLINE_RE,
        re.compile(
            rf"(?:response due by|due by|respond by|file by|filed by|must be filed by|no later than)\s*(?P<date>{_DATE_TOKEN_PATTERN})",
            flags=re.IGNORECASE,
        ),
    )
    for pattern in patterns:
        match = pattern.search(source_text or "")
        if not match:
            continue
        parsed = _parse_date_token(match.group("date"))
        if parsed is not None:
            return parsed
    return None


def _parse_decimal_amount(raw_amount: str) -> Decimal | None:
    amount_text = re.sub(r"[^\d,.\s]", "", str(raw_amount or "")).replace(" ", "")
    if not amount_text:
        return None

    if "," in amount_text and "." in amount_text:
        if amount_text.rfind(".") > amount_text.rfind(","):
            amount_text = amount_text.replace(",", "")
        else:
            amount_text = amount_text.replace(".", "").replace(",", ".")
    elif "," in amount_text:
        parts = amount_text.split(",")
        if len(parts[-1]) in {1, 2}:
            amount_text = "".join(parts[:-1]) + "." + parts[-1]
        else:
            amount_text = "".join(parts)
    elif amount_text.count(".") > 1:
        parts = amount_text.split(".")
        if len(parts[-1]) in {1, 2}:
            amount_text = "".join(parts[:-1]) + "." + parts[-1]
        else:
            amount_text = "".join(parts)

    try:
        return Decimal(amount_text)
    except Exception:
        return None


def _canonical_currency(raw_currency: str) -> str | None:
    normalized = str(raw_currency or "").strip().lower()
    if normalized in {"gbp", "pounds sterling", "£"}:
        return "GBP"
    if normalized in {"usd", "$"}:
        return "USD"
    if normalized in {"eur", "Ń”Đ˛Ń€Đľ", "€"}:
        return "EUR"
    if normalized in {"ĐłŃ€Đ˝", "uah"}:
        return "UAH"
    return None


def _display_search_term(value: str | None) -> str:
    normalized = str(value or "").strip().replace("_", " ")
    mapping = {
        "debt recovery": "debt recovery",
        "civil dispute": "civil dispute",
        "court decision": "court decision",
        "procedural document": "procedural document",
        "claim notice": "claim notice",
    }
    return mapping.get(normalized, normalized)


def _extract_dates(source_text: str) -> list[date]:
    values: list[date] = []
    seen: set[date] = set()
    for raw in _DATE_DMY.findall(source_text or ""):
        parsed = _parse_date_token(raw)
        if parsed is None:
            continue
        if parsed not in seen:
            seen.add(parsed)
            values.append(parsed)
    for raw in _DATE_DMY_SLASH.findall(source_text or ""):
        parsed = _parse_date_token(raw)
        if parsed is None:
            continue
        if parsed not in seen:
            seen.add(parsed)
            values.append(parsed)
    for raw in _DATE_YMD.findall(source_text or ""):
        parsed = _parse_date_token(raw)
        if parsed is None:
            continue
        if parsed not in seen:
            seen.add(parsed)
            values.append(parsed)
    for raw in _DATE_TEXTUAL.findall(source_text or ""):
        parsed = _parse_date_token(raw)
        if parsed is None:
            continue
        if parsed not in seen:
            seen.add(parsed)
            values.append(parsed)
    values.sort()
    return values


def _extract_financial_exposure(source_text: str) -> tuple[Decimal | None, str | None, str | None]:
    match = _MONEY_RE.search(source_text or "")
    if not match:
        return None, None, None

    raw_amount = match.group(1).replace(" ", "").replace(",", ".")
    try:
        amount = Decimal(raw_amount)
    except Exception:
        return None, None, None

    raw_currency = (match.group(2) or "").strip().lower()
    currency = "UAH"
    if raw_currency in {"usd", "$"}:
        currency = "USD"
    elif raw_currency in {"eur", "євро"}:
        currency = "EUR"

    text = _normalized(source_text)
    exposure_type = "claim"
    if "штраф" in text or "penalty" in text:
        exposure_type = "penalty"
    elif "збитк" in text or "damages" in text:
        exposure_type = "damages"
    elif "борг" in text or "debt" in text:
        exposure_type = "debt"
    return amount, currency, exposure_type


def _detect_language(source_text: str) -> str:
    text = str(source_text or "")
    cyr = len(re.findall(r"[А-Яа-яІіЇїЄєҐґ]", text))
    lat = len(re.findall(r"[A-Za-z]", text))
    if cyr > 20 and lat > 20:
        return "mixed"
    if cyr > lat:
        return "uk"
    if lat > cyr:
        return "en"
    return "unknown"


def _detect_classified_type(source_text: str) -> str:
    text = _normalized(source_text)
    if any(marker in text for marker in ("постанова", "ухвала", "рішення суду", "апеляційний суд", "верховний суд")):
        return "court_decision"
    if any(marker in text for marker in ("договір", "contract", "угода", "agreement")):
        return "contract"
    if any(marker in text for marker in ("позовна заява", "апеляційна скарга", "касаційна скарга")):
        return "procedural_document"
    if any(marker in text for marker in ("претензія", "demand letter", "претенз")):
        return "claim_notice"
    return "other"


def _detect_subject_matter(source_text: str) -> str:
    text = _normalized(source_text)
    if any(marker in text for marker in ("кредит", "позик", "борг", "стягнен")):
        return "debt_recovery"
    if any(marker in text for marker in ("труд", "звільнен", "заробітн")):
        return "labor"
    if any(marker in text for marker in ("алімент", "шлюб", "подруж")):
        return "family"
    if any(marker in text for marker in ("адміністратив", "державн", "виконавч")):
        return "administrative"
    return "civil_dispute"


def _detect_party_role(source_text: str) -> str | None:
    text = _normalized(source_text)
    if "позивач" in text:
        return "plaintiff"
    if "відповідач" in text:
        return "defendant"
    if "боржник" in text:
        return "debtor"
    if "кредитор" in text:
        return "creditor"
    return None


def _extract_parties(source_text: str) -> list[dict[str, str]]:
    patterns: tuple[tuple[str, str], ...] = (
        ("plaintiff", r"(?:позивач|plaintiff)\s*[:\-]\s*([^\n\r]+)"),
        ("defendant", r"(?:відповідач|defendant)\s*[:\-]\s*([^\n\r]+)"),
        ("creditor", r"(?:кредитор)\s*[:\-]\s*([^\n\r]+)"),
        ("debtor", r"(?:боржник)\s*[:\-]\s*([^\n\r]+)"),
    )
    found: list[dict[str, str]] = []
    for role, pattern in patterns:
        match = re.search(pattern, source_text or "", flags=re.IGNORECASE)
        if not match:
            continue
        name = re.sub(r"\s+", " ", match.group(1)).strip(" ,.;:")
        if name:
            found.append({"name": name, "role": role})
    return found[:6]


def _detect_jurisdiction(source_text: str) -> str:
    text = _normalized(source_text)
    if any(marker in text for marker in ("цк україни", "цпк україни", "кас україни", "верховний суд")):
        return "UA"
    if "european union" in text or "eu regulation" in text:
        return "EU"
    return "OTHER"


def _guess_deadline(classified_type: str, source_text: str, doc_date: date | None) -> date | None:
    if doc_date is None:
        return None
    text = _normalized(source_text)
    if classified_type == "court_decision" and ("апеляц" in text or "рішення суду" in text):
        return doc_date + timedelta(days=settings.appeal_deadline_days)
    if "касаці" in text:
        return doc_date + timedelta(days=settings.cassation_deadline_days)
    return None


def _detect_issues(
    *,
    source_text: str,
    classified_type: str,
    doc_date: date | None,
    deadline: date | None,
    amount: Decimal | None,
) -> tuple[str, str, str, str, list[dict[str, str]]]:
    text = _normalized(source_text)
    legal = "medium"
    procedural = "medium"
    financial = "low"
    urgency = "medium"
    issues: list[dict[str, str]] = []

    if classified_type == "court_decision" and "ст. 625" in text:
        legal = "high"
        snippet = next((line for line in source_text.split('\n') if "ст. 625" in line.lower()), "ст. 625")
        start = source_text.lower().find(snippet.lower())
        issues.append(
            {
                "issue_type": "article_625_exposure",
                "severity": "high",
                "description": "Потрібна актуальна практика ВС по ст. 625 ЦК України.",
                "impact": "Ризик втрати частини вимог без чіткої прецедентної аргументації.",
                "snippet": snippet,
                "start_index": start if start >= 0 else None,
                "end_index": start + len(snippet) if start >= 0 else None,
            }
        )

    if deadline is not None:
        days_left = (deadline - date.today()).days
        if days_left < 0:
            urgency = "critical"
            procedural = "high"
            snippet = next((line for line in source_text.split('\n') if any(token in line.lower() for token in ("постанова", "ухвала", "рішення"))), None)
            start = source_text.lower().find(snippet.lower()) if snippet else -1
            issues.append(
                {
                    "issue_type": "deadline_missed",
                    "severity": "critical",
                    "description": "Процесуальний строк уже пропущено.",
                    "impact": "Потрібна заява про поновлення строку або альтернативний маршрут.",
                    "snippet": snippet,
                    "start_index": start if start >= 0 else None,
                    "end_index": start + len(snippet) if start >= 0 else None,
                }
            )
        elif days_left <= 5:
            urgency = "critical"
            procedural = "high"
        elif days_left <= 10:
            urgency = "high"

    if amount is not None and amount >= Decimal("500000"):
        financial = "high"
        marker = str(amount).split('.')[0]
        snippet = next((line for line in source_text.split('\n') if marker in line), None)
        start = source_text.find(snippet) if snippet else -1
        issues.append(
            {
                "issue_type": "high_financial_exposure",
                "severity": "high",
                "description": "Висока сума потенційного стягнення.",
                "impact": "Потрібен посилений evidence chain і переговорний contingency план.",
                "snippet": snippet,
                "start_index": start if start >= 0 else None,
                "end_index": start + len(snippet) if start >= 0 else None,
            }
        )
    elif amount is not None and amount >= Decimal("100000"):
        financial = "medium"

    if doc_date and (date.today() - doc_date).days > 365 * 2:
        legal = "high" if legal != "high" else legal
        marker = doc_date.strftime("%Y") if hasattr(doc_date, 'strftime') else str(doc_date)
        snippet = next((line for line in source_text.split('\n') if marker in line), None)
        start = source_text.find(snippet) if snippet else -1
        issues.append(
            {
                "issue_type": "aging_case_risk",
                "severity": "medium",
                "description": "Історичний документ: потрібна перевірка строків і актуальності практики.",
                "impact": "Підвищений ризик процесуальних бар'єрів.",
                "snippet": snippet,
                "start_index": start if start >= 0 else None,
                "end_index": start + len(snippet) if start >= 0 else None,
            }
        )

    if not issues:
        issues.append(
            {
                "issue_type": "baseline_review",
                "severity": "low",
                "description": "Критичні прогалини автоматично не виявлено.",
                "impact": "Потрібен lawyer-in-the-loop review перед поданням.",
            }
        )
        urgency = "low"

    return legal, procedural, financial, urgency, issues[:8]


async def _ai_classify(source_text: str, *, deep: bool = False) -> dict[str, Any]:
    system_prompt = (
        "Ти — експерт-аналітик юридичних документів України (Senior Legal Analyst). "
        "Твоє завдання: провести глибокий intake-аналіз документа та структурувати його в JSON.\n"
        "ПРАВИЛА:\n"
        "1. Повертай ТІЛЬКИ валідний JSON.\n"
        "2. Не вигадуй дані. Якщо інформації немає - став null.\n"
        "3. Будь максимально точним у класифікації та оцінці ризиків."
    )
    
    if deep:
        system_prompt += (
            "\nDEEP AUDIT MODE: Зверни увагу на приховані деталі, непрямі вказівки на ризики, "
            "можливі процесуальні пастки та неточності у формулюваннях. "
            "В 'detected_issues' наведи більш детальні та критичні зауваження."
        )

    user_prompt = (
        "Проаналізуй поданий текст і витягни наступні поля у форматі JSON:\n"
        "{\n"
        '  "classified_type": "court_decision|contract|procedural_document|claim_notice|other",\n'
        '  "document_language": "uk|en|mixed",\n'
        '  "jurisdiction": "UA|EU|OTHER",\n'
        '  "primary_party_role": "plaintiff|defendant|creditor|debtor|null",\n'
        '  "subject_matter": "debt_recovery|labor|family|administrative|civil_dispute|...",\n'
        '  "risk_level_legal": "low|medium|high",\n'
        '  "risk_level_procedural": "low|medium|high",\n'
        '  "risk_level_financial": "low|medium|high",\n'
        '  "urgency_level": "low|medium|high|critical",\n'
        '  "detected_issues": [\n'
        '    {"issue_type": "string", "severity": "low|medium|high|critical", "description": "string", "impact": "string", "snippet": "EXACT_TEXT_FRAGMENT", "start_index": char_offset_start, "end_index": char_offset_end}\n'
        '  ],\n'
        '  "classifier_confidence": 0.0\n'
        "}\n\n"
        f"ТЕКСТ ДОКУМЕНТА:\n{source_text[:12000 if deep else 6000]}"
    )

    ai_result = await generate_legal_document_for_role(
        "intake",
        user_prompt,
        deep=deep
    )
    
    if not ai_result.used_ai:
        return {}
    parsed = _parse_json_object(ai_result.text)
    if parsed:
        parsed["classifier_model"] = ai_result.model or ""
    return parsed


async def classify_document_intake(source_text: str, *, mode: str = "standard") -> dict[str, Any]:
    deep = (mode == "deep")
    text = str(source_text or "").strip()
    jurisdiction = _detect_jurisdiction(text)
    classified_type = _detect_classified_type(text)
    dates = _extract_dates(text)
    doc_date = dates[-1] if dates else None
    deadline = _guess_deadline(classified_type, text, doc_date)
    amount, currency, exposure_type = _extract_financial_exposure(text)
    legal, procedural, financial, urgency, issues = _detect_issues(
        source_text=text,
        classified_type=classified_type,
        doc_date=doc_date,
        deadline=deadline,
        amount=amount,
    )

    heuristic_confidence = 0.72 if classified_type != "other" else 0.58
    if _is_uk_jurisdiction(jurisdiction):
        heuristic_confidence = min(0.88, heuristic_confidence + 0.04)

    payload: dict[str, Any] = {
        "classified_type": classified_type,
        "document_language": _detect_language(text),
        "jurisdiction": jurisdiction,
        "primary_party_role": _detect_party_role(text),
        "identified_parties": _extract_parties(text),
        "subject_matter": _detect_subject_matter(text),
        "financial_exposure_amount": amount,
        "financial_exposure_currency": currency,
        "financial_exposure_type": exposure_type,
        "document_date": doc_date,
        "deadline_from_document": deadline,
        "urgency_level": urgency,
        "risk_level_legal": legal,
        "risk_level_procedural": procedural,
        "risk_level_financial": financial,
        "detected_issues": issues,
        "classifier_confidence": heuristic_confidence,
        "classifier_model": "heuristic-intake-v2",
        "raw_text_preview": text[:2000],
    }

    if deep:
        ai_payload = await _ai_classify(text, deep=True)
        if ai_payload:
            for key in (
                "classified_type",
                "document_language",
                "jurisdiction",
                "primary_party_role",
                "subject_matter",
                "risk_level_legal",
                "risk_level_procedural",
                "risk_level_financial",
                "urgency_level",
                "detected_issues",
                "classifier_confidence",
                "classifier_model",
            ):
                value = ai_payload.get(key)
                if value not in (None, "", []):
                    payload[key] = value
    return payload


def create_document_analysis_intake(
    db: Session,
    *,
    user_id: str,
    source_file_name: str | None,
    source_text: str,
    intake_payload: dict[str, Any],
) -> DocumentAnalysisIntake:
    row = DocumentAnalysisIntake(
        user_id=user_id,
        source_file_name=source_file_name,
        source_text=source_text,
        classified_type=str(intake_payload.get("classified_type") or "other"),
        document_language=str(intake_payload.get("document_language") or "unknown"),
        jurisdiction=str(intake_payload.get("jurisdiction") or "UA"),
        primary_party_role=str(intake_payload.get("primary_party_role") or "") or None,
        identified_parties=intake_payload.get("identified_parties") or [],
        subject_matter=str(intake_payload.get("subject_matter") or "") or None,
        financial_exposure_amount=intake_payload.get("financial_exposure_amount"),
        financial_exposure_currency=str(intake_payload.get("financial_exposure_currency") or "") or None,
        financial_exposure_type=str(intake_payload.get("financial_exposure_type") or "") or None,
        document_date=intake_payload.get("document_date"),
        deadline_from_document=intake_payload.get("deadline_from_document"),
        urgency_level=str(intake_payload.get("urgency_level") or "medium"),
        risk_level_legal=str(intake_payload.get("risk_level_legal") or "medium"),
        risk_level_procedural=str(intake_payload.get("risk_level_procedural") or "medium"),
        risk_level_financial=str(intake_payload.get("risk_level_financial") or "low"),
        detected_issues=intake_payload.get("detected_issues") or [],
        classifier_confidence=float(intake_payload.get("classifier_confidence") or 0.6),
        classifier_model=str(intake_payload.get("classifier_model") or "heuristic-intake-v1"),
        raw_text_preview=str(intake_payload.get("raw_text_preview") or source_text[:2000]),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_document_analysis_intake(db: Session, *, user_id: str, intake_id: str) -> DocumentAnalysisIntake | None:
    row = db.get(DocumentAnalysisIntake, intake_id)
    if row is None or row.user_id != user_id:
        return None
    return row


def _query_for_intake(intake: DocumentAnalysisIntake) -> str:
    parts = [str(intake.subject_matter or "").strip(), str(intake.classified_type or "").strip()]
    preview = _normalized(intake.raw_text_preview or "")
    if "ст. 625" in preview:
        parts.append("ст. 625 ЦК України")
    if "порук" in preview:
        parts.append("порука")
    if "апеляц" in preview:
        parts.append("апеляційна скарга")
    joined = " ".join(item for item in parts if item)
    return joined or "верховний суд цивільна справа"


def _bucket_case_law_pattern(summary: str, decision_date: date | None) -> str:
    text = _normalized(summary)
    if any(marker in text for marker in ("відмов", "залишити без задоволення позов", "не підлягає задоволенню")):
        return "losing_pattern"
    if any(marker in text for marker in ("задовольн", "стягнен", "підлягає стягненню", "скасувати рішення")):
        return "winning_pattern"
    if decision_date and (date.today() - decision_date).days <= 365:
        return "emerging_pattern"
    return "neutral_pattern"


def build_precedent_groups_for_intake_ua(
    db: Session,
    *,
    user_id: str,
    intake: DocumentAnalysisIntake,
    limit: int = 15,
) -> tuple[list[CaseLawPrecedentGroup], list[dict[str, Any]]]:
    safe_limit = max(6, min(limit, 30))
    query = _query_for_intake(intake)

    search_result = search_case_law(
        db,
        query=query,
        only_supreme=True,
        page=1,
        page_size=safe_limit,
        sort_by="decision_date",
        sort_dir="desc",
    )
    rows = search_result.items
    if not rows:
        fallback = search_case_law(
            db,
            query=query,
            only_supreme=False,
            page=1,
            page_size=safe_limit,
            sort_by="decision_date",
            sort_dir="desc",
        )
        rows = fallback.items
    if not rows:
        broad = search_case_law(
            db,
            query=None,
            only_supreme=False,
            page=1,
            page_size=safe_limit,
            sort_by="decision_date",
            sort_dir="desc",
        )
        rows = broad.items

    db.execute(
        delete(CaseLawPrecedentGroup).where(
            CaseLawPrecedentGroup.user_id == user_id,
            CaseLawPrecedentGroup.intake_id == intake.id,
        )
    )
    db.flush()

    buckets: dict[str, list[Any]] = {
        "winning_pattern": [],
        "losing_pattern": [],
        "neutral_pattern": [],
        "emerging_pattern": [],
    }
    refs: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        pattern_type = _bucket_case_law_pattern(row.summary or "", row.decision_date)
        buckets[pattern_type].append(row)
        refs.append(
            {
                "id": row.id,
                "source": row.source,
                "decision_id": row.decision_id,
                "case_number": row.case_number,
                "court_name": row.court_name,
                "decision_date": row.decision_date.isoformat() if row.decision_date else None,
                "summary": row.summary,
                "pattern_type": pattern_type,
                "relevance_score": round(max(0.1, 1.0 - (index - 1) * 0.06), 2),
            }
        )

    groups: list[CaseLawPrecedentGroup] = []
    for pattern_type, items in buckets.items():
        if not items:
            continue
        strength = min(0.95, 0.45 + len(items) * 0.07)
        counter_arguments = [
            "Опонент посилатиметься на відсутність належних доказів ключових фактів.",
            "Опонент акцентуватиме на пропуску строків та процесуальних дефектах.",
        ]
        group = CaseLawPrecedentGroup(
            user_id=user_id,
            intake_id=intake.id,
            pattern_type=pattern_type,
            pattern_description=f"Група {pattern_type} для запиту: {query}",
            precedent_ids=[item.id for item in items],
            precedent_count=len(items),
            pattern_strength=round(strength, 2),
            counter_arguments=counter_arguments,
            mitigation_strategy="Закрити процесуальні дефекти до подання та підсилити доказову матрицю.",
            strategic_advantage="Сегментація практики на виграшні/ризикові сценарії.",
            vulnerability_to_appeal="Середня. Потрібно appeal-proof обґрунтування по кожній ключовій тезі.",
        )
        db.add(group)
        groups.append(group)

    db.commit()
    for row in groups:
        db.refresh(row)
    return groups, refs


def list_precedent_groups(db: Session, *, user_id: str, intake_id: str) -> list[CaseLawPrecedentGroup]:
    stmt = (
        select(CaseLawPrecedentGroup)
        .where(CaseLawPrecedentGroup.user_id == user_id, CaseLawPrecedentGroup.intake_id == intake_id)
        .order_by(desc(CaseLawPrecedentGroup.created_at))
    )
    return list(db.execute(stmt).scalars().all())


async def build_strategy_blueprint_ua(
    db: Session,
    *,
    user_id: str,
    intake: DocumentAnalysisIntake,
    precedent_groups: list[CaseLawPrecedentGroup],
    regenerate: bool = True,
) -> LegalStrategyBlueprint:
    if regenerate:
        db.execute(
            delete(LegalStrategyBlueprint).where(
                LegalStrategyBlueprint.user_id == user_id,
                LegalStrategyBlueprint.intake_id == intake.id,
            )
        )
        db.flush()

    winning_group = next((item for item in precedent_groups if item.pattern_type == "winning_pattern"), None)
    winning_strength = float(winning_group.pattern_strength or 0.0) if winning_group else 0.0
    high_risk = any(
        str(value or "").lower() == "high"
        for value in (intake.risk_level_legal, intake.risk_level_procedural, intake.risk_level_financial)
    )
    base_win = 0.62 + winning_strength * 0.2 - (0.12 if high_risk else 0.0)
    base_win = max(0.15, min(base_win, 0.85))

    immediate_actions = [
        {
            "action": "Закрити доказові прогалини по ключових фактах.",
            "deadline": (date.today() + timedelta(days=3)).isoformat(),
            "rationale": "Без суцільного evidence chain зростає ризик відмови.",
            "evidence_to_collect": ["договірні документи", "платіжні/банківські документи", "листування"],
        },
        {
            "action": "Підготувати preemption-карту очікуваних аргументів опонента.",
            "deadline": (date.today() + timedelta(days=5)).isoformat(),
            "rationale": "Counter-argument preemption підвищує стійкість документа в апеляції.",
            "evidence_to_collect": ["практика ВС", "процесуальні докази"],
        },
    ]
    if intake.deadline_from_document is not None:
        immediate_actions.insert(
            0,
            {
                "action": "Контроль процесуального строку по документу.",
                "deadline": intake.deadline_from_document if isinstance(intake.deadline_from_document, str) else intake.deadline_from_document.isoformat(),
                "rationale": "Пропуск строку є критичним процесуальним ризиком.",
                "evidence_to_collect": ["докази дати отримання/складання документа"],
            },
        )

    # Call SWOT Agent for deep analysis
    swot_payload = {
        "strengths": ["Strong fact summary from intake", "Solid procedural alignment"],
        "weaknesses": ["Evidence gaps detected in initial scan", "Tight deadlines"],
        "opportunities": ["Leverage recent supreme court precedents", "Procedural preemption"],
        "threats": ["Counter-arguments on admissibility", "Appeal risks"],
        "win_probability": round(base_win, 2)
    }
    
    try:
        # We wrap this to avoid breaking the flow if AI fails
        intake_dict = {
            "classified_type": intake.classified_type,
            "subject_matter": intake.subject_matter,
            "risk_level_legal": intake.risk_level_legal,
            "detected_issues": intake.detected_issues,
            "raw_text_preview": intake.raw_text_preview
        }
        groups_dict = [
            {
                "pattern_type": pg.pattern_type,
                "pattern_description": pg.pattern_description,
                "pattern_strength": pg.pattern_strength
            }
            for pg in precedent_groups
        ]
        ai_swot, _ = await run_swot_agent(intake=intake_dict, precedent_groups=groups_dict)
        if ai_swot:
            swot_payload = ai_swot
    except Exception as e:
        print(f"SWOT Agent failed: {e}")

    blueprint = LegalStrategyBlueprint(
        user_id=user_id,
        intake_id=intake.id,
        precedent_group_id=winning_group.id if winning_group else (precedent_groups[0].id if precedent_groups else None),
        immediate_actions=immediate_actions,
        procedural_roadmap=[
            {
                "step": 1,
                "legal_action": "Pre-filing validation та формування позиції.",
                "expected_outcome": "Готовий до подання процесуальний пакет.",
                "pivot_if_lost": "Термінове усунення дефектів і повторна подача.",
            },
            {
                "step": 2,
                "legal_action": "Подання основного документа з процесуальними клопотаннями.",
                "expected_outcome": "Відкриття провадження і фіксація рамки спору.",
                "pivot_if_lost": "Апеляційний/альтернативний процедурний маршрут.",
            },
        ],
        evidence_strategy=[
            {
                "phase": "Перша інстанція",
                "evidence_type": "Письмові первинні докази",
                "admissibility": "висока",
                "impact": "формують базу відповідальності",
            },
            {
                "phase": "Апеляція",
                "evidence_type": "Докази процесуальних помилок та помилок застосування права",
                "admissibility": "середня",
                "impact": "підсилюють шанс перегляду рішення",
            },
        ],
        negotiation_playbook=[
            {
                "counterparty_offer": "Часткове визнання без компенсації витрат",
                "our_counter": "Прийнятно лише з покриттям витрат і чітким строком виконання",
                "reasoning": "Захист процесуального та фінансового результату",
            }
        ],
        risk_heat_map=[
            {
                "scenario": "Повний виграш",
                "likelihood_pct": round(swot_payload.get("win_probability", base_win) * 100, 1),
                "consequences": "Максимальне досягнення цілей спору",
                "mitigation": "Підтримувати доказову дисципліну і посилання на ВС",
            },
            {
                "scenario": "Частковий виграш",
                "likelihood_pct": round((1 - swot_payload.get("win_probability", base_win)) * 45, 1),
                "consequences": "Часткове задоволення вимог",
                "mitigation": "Посилити розрахунки та причинно-наслідковий зв'язок",
            },
            {
                "scenario": "Програш",
                "likelihood_pct": round((1 - swot_payload.get("win_probability", base_win)) * 35, 1),
                "consequences": "Перехід до апеляції/виконання",
                "mitigation": "Готувати апеляційний резерв та переговорний трек",
            },
        ],
        critical_deadlines=[
            {
                "event": "Оновлення доказового пакета",
                "due_date": (date.today() + timedelta(days=5)).isoformat(),
                "risk_if_missed": "Зниження шансів на позитивний процесуальний результат",
            }
        ],
        swot_analysis=swot_payload,
        win_probability=swot_payload.get("win_probability", base_win),
        financial_strategy=swot_payload.get("financial_strategy"),
        timeline_projection=swot_payload.get("timeline_projection"),
        penalty_forecast=swot_payload.get("penalty_forecast"),
        confidence_score=round(float(swot_payload.get("win_probability") or base_win), 2),
        confidence_rationale="Скоринг базується на AI SWOT аналізі, ризик-профілі та силі виграшних прецедентів.",
        recommended_next_steps=(
            "1) Опрацювати виявлені SWOT-ризики. "
            "2) Закрити критичні evidence gaps. "
            "3) Оцінити фінансову доцільність та розрахувати санкції."
        ),
    )
    # Fix SWOT keys for frontend alignment
    if isinstance(blueprint.swot_analysis, dict):
        blueprint.swot_analysis = {
            "strengths": blueprint.swot_analysis.get("strengths") or [],
            "weaknesses": blueprint.swot_analysis.get("weaknesses") or [],
            "opportunities": blueprint.swot_analysis.get("opportunities") or [],
            "threats": blueprint.swot_analysis.get("threats") or []
        }

    db.add(blueprint)
    db.commit()
    db.refresh(blueprint)
    return blueprint


def get_strategy_blueprint(db: Session, *, user_id: str, strategy_id: str) -> LegalStrategyBlueprint | None:
    row = db.get(LegalStrategyBlueprint, strategy_id)
    if row is None or row.user_id != user_id:
        return None
    return row


def bind_strategy_to_document(db: Session, *, strategy: LegalStrategyBlueprint, document_id: str) -> LegalStrategyBlueprint:
    strategy.document_id = document_id
    db.add(strategy)
    db.commit()
    db.refresh(strategy)
    return strategy


def create_document_generation_audit(
    db: Session,
    *,
    document_id: str,
    strategy_blueprint_id: str | None,
    precedent_citations: list[str] | None,
    counter_argument_addresses: list[str] | None,
    evidence_positioning_notes: str,
    procedure_optimization_notes: str,
    appeal_proofing_notes: str,
) -> DocumentGenerationAudit:
    row = DocumentGenerationAudit(
        document_id=document_id,
        strategy_blueprint_id=strategy_blueprint_id,
        precedent_citations=precedent_citations or [],
        counter_argument_addresses=counter_argument_addresses or [],
        evidence_positioning_notes=evidence_positioning_notes,
        procedure_optimization_notes=procedure_optimization_notes,
        appeal_proofing_notes=appeal_proofing_notes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_document_generation_audit(
    db: Session,
    *,
    user_id: str,
    document_id: str,
) -> DocumentGenerationAudit | None:
    document = db.get(GeneratedDocument, document_id)
    if document is None or document.user_id != user_id:
        return None
    stmt = (
        select(DocumentGenerationAudit)
        .where(DocumentGenerationAudit.document_id == document_id)
        .order_by(desc(DocumentGenerationAudit.generated_at))
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


# --- Legacy (UA) Implementation fallbacks to avoid recursion ---

def _legacy_extract_financial_exposure(source_text: str) -> tuple[Decimal | None, str | None, str | None]:
    text = _normalized(source_text)
    match = _MONEY_RE.search(source_text or "")
    if match:
        raw_amount = match.group(1)
        raw_currency = match.group(2)
        amount = _parse_decimal_amount(raw_amount)
        currency = _canonical_currency(raw_currency)
        if "штраф" in text or "пеня" in text:
            return amount, currency, "penalty"
        return amount, currency, "claim"
    return None, None, None

def _legacy_detect_classified_type(source_text: str) -> str:
    text = _normalized(source_text)
    if any(m in text for m in ("рішення", "постанова", "ухвала")):
        return "court_decision"
    if any(m in text for m in ("скарга", "позов", "відзив", "заява")):
        return "procedural_document"
    if any(m in text for m in ("вимога", "претензія", "повідомлення")):
        return "claim_notice"
    return "other"

def _legacy_detect_subject_matter(source_text: str) -> str:
    text = _normalized(source_text)
    if any(m in text for m in ("борг", "позика", "кредит", "стягнення")):
        return "debt_recovery"
    if any(m in text for m in ("прац", "звільн", "зарплат")):
        return "labor"
    if any(m in text for m in ("сімейн", "розлуч", "алімент")):
        return "family"
    if any(m in text for m in ("адмініст", "податк", "митн")):
        return "administrative"
    return ""

def _legacy_detect_party_role(source_text: str) -> str | None:
    text = _normalized(source_text)
    if "позивач" in text or "скаржник" in text:
        return "claimant"
    if "відповідач" in text or "боржник" in text:
        return "defendant"
    return None

def _legacy_extract_parties(source_text: str) -> list[dict[str, str]]:
    text = str(source_text or "")
    appellant = _APPELLANT_RE.search(text)
    other = _OTHER_PARTY_RE.search(text)
    found = []
    if appellant:
        found.append({"role": "claimant", "name": appellant.group(1).strip()})
    if other:
        found.append({"role": "defendant", "name": other.group(1).strip()})
    return found

def _legacy_detect_jurisdiction(source_text: str) -> str:
    text = _normalized(source_text)
    if "суд" in text or "україни" in text:
        return "UA"
    return "UA"

def _legacy_guess_deadline(classified_type: str, source_text: str, doc_date: date | None) -> date | None:
    if doc_date and classified_type == "court_decision":
        return doc_date + timedelta(days=30)
    if doc_date and classified_type == "claim_notice":
        return doc_date + timedelta(days=10)
    return None

def _legacy_detect_issues(
    *,
    source_text: str,
    classified_type: str,
    doc_date: date | None,
    deadline: date | None,
    amount: Decimal | None,
) -> tuple[str, str, str, str, list[dict[str, str]]]:
    issues = []
    urgency = "medium"
    if deadline:
        days = (deadline - date.today()).days
        if days < 3: urgency = "critical"
        elif days < 7: urgency = "high"
    if amount and amount > 100000:
        issues.append({"issue_type": "high_exposure", "severity": "high", "description": "Значна сума спору", "impact": "Фінансові ризики"})
    return "medium", "medium", "low" if not amount else "medium", urgency, issues

def _legacy_ai_classify(source_text: str) -> dict[str, Any]:
    return {}

def _legacy_query_for_intake(intake: DocumentAnalysisIntake) -> str:
    parts = [str(intake.subject_matter or ""), str(intake.classified_type or "")]
    return " ".join(p for p in parts if p) or "supreme court ukraine"

def _legacy_bucket_case_law_pattern(summary: str, decision_date: date | None) -> str:
    text = _normalized(summary)
    if "задовольнити" in text: return "winning_pattern"
    if "відмовити" in text: return "losing_pattern"
    return "neutral_pattern"

# Note: build_precedent_groups_for_intake and build_strategy_blueprint (Legacy) 
# have their own deep logic which is not recursive because they don't call the wrapper.
# So I will just keep the pointers to the ACTUAL UA functions defined at the beginning of the file.


def _text_mentions_uk_context(source_text: str) -> bool:
    text = _normalized(source_text)
    return any(
        marker in text
        for marker in (
            "england and wales",
            "high court of justice",
            "county court",
            "claimant",
            "defendant",
            "judgment",
            "claim form",
            "letter before claim",
            "hmcts",
            "uksc",
            "ewhc",
            "ewca",
            "n244",
            "n1",
        )
    )


def _unique_nonempty_strings(values: list[str]) -> list[str]:
    items: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = re.sub(r"\s+", " ", str(value or "").strip())
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        items.append(normalized)
    return items


def _extract_financial_exposure(source_text: str) -> tuple[Decimal | None, str | None, str | None]:
    match = _MONEY_BEFORE_RE.search(source_text or "")
    raw_currency = ""
    raw_amount = ""
    if match:
        raw_currency = match.group(1) or ""
        raw_amount = match.group(2) or ""
    else:
        match = _MONEY_AFTER_RE.search(source_text or "")
        if match:
            raw_amount = match.group(1) or ""
            raw_currency = match.group(2) or ""

    if raw_amount and raw_currency:
        amount = _parse_decimal_amount(raw_amount)
        currency = _canonical_currency(raw_currency)
        if amount is not None and currency is not None:
            text = _normalized(source_text)
            exposure_type = "claim"
            if "penalty" in text:
                exposure_type = "penalty"
            elif "damages" in text:
                exposure_type = "damages"
            elif any(marker in text for marker in ("debt", "arrears", "loan", "outstanding balance")):
                exposure_type = "debt"
            return amount, currency, exposure_type

    return _legacy_extract_financial_exposure(source_text)


def _detect_classified_type(source_text: str) -> str:
    text = _normalized(source_text)
    if any(
        marker in text
        for marker in (
            "judgment",
            "order",
            "high court of justice",
            "county court",
            "court of appeal",
            "uk supreme court",
            "uksc",
            "ewhc",
            "ewca",
            "employment tribunal",
            "upper tribunal",
            "first-tier tribunal",
        )
    ):
        return "court_decision"
    if any(marker in text for marker in ("claim form", "particulars of claim", "witness statement", "defence", "defense", "application notice", "appellant's notice", "respondent's notice", "n244", "n1", "grounds of appeal", "skeleton argument")):
        return "procedural_document"
    if any(marker in text for marker in ("letter before claim", "letter before action", "pre-action protocol", "statutory demand", "demand letter")):
        return "claim_notice"
    return _legacy_detect_classified_type(source_text)


def _detect_subject_matter(source_text: str) -> str:
    text = _normalized(source_text)
    if any(marker in text for marker in ("debt", "loan", "arrears", "outstanding balance", "invoice", "damages", "recovery")):
        return "debt_recovery"
    if any(marker in text for marker in ("employment tribunal", "unfair dismissal", "redundancy", "wages", "salary")):
        return "labor"
    if any(marker in text for marker in ("divorce", "children act", "custody", "contact order", "financial remedy")):
        return "family"
    if any(marker in text for marker in ("judicial review", "public authority", "tribunal decision", "planning appeal", "immigration")):
        return "administrative"
    return _legacy_detect_subject_matter(source_text)


def _detect_party_role(source_text: str) -> str | None:
    text = _normalized(source_text)
    for marker, role in (
        ("claimant", "claimant"),
        ("defendant", "defendant"),
        ("applicant", "applicant"),
        ("respondent", "respondent"),
        ("appellant", "appellant"),
        ("petitioner", "petitioner"),
    ):
        if marker in text:
            return role
    return _legacy_detect_party_role(source_text)


def _extract_parties(source_text: str) -> list[dict[str, str]]:
    patterns: tuple[tuple[str, str], ...] = (
        ("claimant", r"(?:claimant)\s*[:\-]\s*([^\n\r]+)"),
        ("defendant", r"(?:defendant)\s*[:\-]\s*([^\n\r]+)"),
        ("applicant", r"(?:applicant)\s*[:\-]\s*([^\n\r]+)"),
        ("respondent", r"(?:respondent)\s*[:\-]\s*([^\n\r]+)"),
        ("appellant", r"(?:appellant)\s*[:\-]\s*([^\n\r]+)"),
        ("petitioner", r"(?:petitioner)\s*[:\-]\s*([^\n\r]+)"),
    )
    found: list[dict[str, str]] = []
    for role, pattern in patterns:
        match = re.search(pattern, source_text or "", flags=re.IGNORECASE)
        if not match:
            continue
        name = re.sub(r"\s+", " ", match.group(1)).strip(" ,.;:")
        if name:
            found.append({"name": name, "role": role})
    return found[:6] or _legacy_extract_parties(source_text)


def _detect_jurisdiction(source_text: str) -> str:
    text = _normalized(source_text)
    if any(marker in text for marker in ("england and wales", "e&w", "ewca", "ewhc", "county court", "high court of justice", "business and property courts")):
        return "EW"
    if any(marker in text for marker in ("united kingdom", "uk supreme court", "uksc", "hmcts", "employment tribunal", "upper tribunal", "first-tier tribunal")):
        return "UK"
    return _legacy_detect_jurisdiction(source_text)


def _guess_deadline(
    classified_type: str,
    source_text: str,
    doc_date: date | None,
    jurisdiction: str | None = None,
) -> date | None:
    explicit_deadline = _extract_explicit_deadline(source_text)
    if explicit_deadline is not None:
        return explicit_deadline
    if _is_uk_jurisdiction(jurisdiction):
        return None
    return _legacy_guess_deadline(classified_type, source_text, doc_date)


def _detect_issues(
    *,
    source_text: str,
    classified_type: str,
    doc_date: date | None,
    deadline: date | None,
    amount: Decimal | None,
    currency: str | None = None,
    jurisdiction: str | None = None,
) -> tuple[str, str, str, str, list[dict[str, str]]]:
    if not _is_uk_jurisdiction(jurisdiction):
        return _legacy_detect_issues(
            source_text=source_text,
            classified_type=classified_type,
            doc_date=doc_date,
            deadline=deadline,
            amount=amount,
        )

    text = _normalized(source_text)
    legal = "medium"
    procedural = "medium"
    financial = "low"
    urgency = "medium"
    issues: list[dict[str, str]] = []

    if classified_type == "claim_notice" and any(marker in text for marker in ("letter before claim", "pre-action protocol")):
        issues.append(
            {
                "issue_type": "pre_action_protocol_review",
                "severity": "medium",
                "description": "Check compliance with the pre-action protocol and service steps.",
                "impact": "Non-compliance can weaken costs position and invite procedural objections.",
            }
        )

    if deadline is not None:
        days_left = (deadline - date.today()).days
        if days_left < 0:
            urgency = "critical"
            procedural = "high"
            issues.append(
                {
                    "issue_type": "deadline_missed",
                    "severity": "critical",
                    "description": "A filing or response deadline appears to have passed.",
                    "impact": "Urgent review is needed to assess extension, relief, or fallback procedure.",
                }
            )
        elif days_left <= 5:
            urgency = "critical"
            procedural = "high"
        elif days_left <= 10:
            urgency = "high"

    high_threshold = Decimal("100000") if currency in {"GBP", "USD", "EUR"} else Decimal("500000")
    medium_threshold = Decimal("25000") if currency in {"GBP", "USD", "EUR"} else Decimal("100000")
    if amount is not None and amount >= high_threshold:
        financial = "high"
        issues.append(
            {
                "issue_type": "high_financial_exposure",
                "severity": "high",
                "description": "The document indicates material financial exposure.",
                "impact": "Strengthen the evidence chain, damages analysis, and settlement fallback position.",
            }
        )
    elif amount is not None and amount >= medium_threshold:
        financial = "medium"

    if doc_date and (date.today() - doc_date).days > 365 * 2:
        legal = "high" if legal != "high" else legal
        issues.append(
            {
                "issue_type": "aging_case_risk",
                "severity": "medium",
                "description": "The source document is relatively old and needs limitation and enforcement review.",
                "impact": "Older matters can carry service, limitation, and procedural record risks.",
            }
        )

    if not issues:
        issues.append(
            {
                "issue_type": "baseline_review",
                "severity": "low",
                "description": "No critical issue was detected automatically.",
                "impact": "Run lawyer review before filing or responding.",
            }
        )
        urgency = "low"

    return legal, procedural, financial, urgency, issues[:8]


async def _ai_classify(source_text: str) -> dict[str, Any]:
    if not _text_mentions_uk_context(source_text):
        return _legacy_ai_classify(source_text)

    ai_result = await generate_legal_document(
        "You classify legal documents across jurisdictions. Return JSON only and detect jurisdiction codes such as UA, EW, UK, EU, or OTHER.",
        (
            "Return JSON with keys "
            '{"classified_type":"","document_language":"","jurisdiction":"","primary_party_role":"","subject_matter":"",'
            '"risk_level_legal":"","risk_level_procedural":"","risk_level_financial":"","urgency_level":"",'
            '"detected_issues":[{"issue_type":"","severity":"","description":"","impact":""}],"classifier_confidence":0.0}\n'
            f"Text:\n{source_text[:15000]}"
        ),
    )
    if not ai_result.used_ai:
        return {}
    parsed = _parse_json_object(ai_result.text)
    if parsed:
        parsed["classifier_model"] = ai_result.model or ""
    return parsed


def _query_candidates_for_intake(intake: DocumentAnalysisIntake) -> list[str]:
    if not _is_uk_jurisdiction(intake.jurisdiction):
        return [_legacy_query_for_intake(intake)]

    preview = _normalized(intake.raw_text_preview or "")
    subject = _display_search_term(intake.subject_matter)
    classified_type = _display_search_term(intake.classified_type)
    candidates: list[str] = []
    if subject and classified_type:
        candidates.append(f"{subject} {classified_type}")
    if subject:
        candidates.append(subject)
    if classified_type:
        candidates.append(classified_type)
    if "judgment" in preview:
        candidates.append("judgment")
    if "order" in preview:
        candidates.append("order")
    if "claim form" in preview or "n1" in preview:
        candidates.append("claim form")
    if "letter before claim" in preview:
        candidates.append("letter before claim")
    if "damages" in preview:
        candidates.append("damages")
    if any(marker in preview for marker in ("debt", "loan", "arrears", "outstanding balance")):
        candidates.append("debt")
    candidates.extend(["uk supreme court", "england and wales"])
    return _unique_nonempty_strings(candidates)


def _query_for_intake(intake: DocumentAnalysisIntake) -> str:
    candidates = _query_candidates_for_intake(intake)
    return candidates[0] if candidates else _legacy_query_for_intake(intake)


def _bucket_case_law_pattern(summary: str, decision_date: date | None) -> str:
    text = _normalized(summary)
    if any(marker in text for marker in ("dismissed", "refused", "denied", "struck out", "rejected")):
        return "losing_pattern"
    if any(marker in text for marker in ("allowed", "granted", "upheld", "succeeded", "judgment for claimant", "awarded damages")):
        return "winning_pattern"
    return _legacy_bucket_case_law_pattern(summary, decision_date)


def build_precedent_groups_for_intake(
    db: Session,
    *,
    user_id: str,
    intake: DocumentAnalysisIntake,
    limit: int = 15,
) -> tuple[list[CaseLawPrecedentGroup], list[dict[str, Any]], str]:
    if not _is_uk_jurisdiction(intake.jurisdiction):
        groups, refs = build_precedent_groups_for_intake_ua(db, user_id=user_id, intake=intake, limit=limit)
        return groups, refs, _legacy_query_for_intake(intake)

    safe_limit = max(6, min(limit, 30))
    query_candidates = _query_candidates_for_intake(intake)
    query_used = query_candidates[0] if query_candidates else "uk civil precedent"
    rows: list[Any] = []

    for only_supreme in (True, False):
        for candidate in query_candidates:
            search_result = search_case_law(
                db,
                query=candidate,
                only_supreme=only_supreme,
                page=1,
                page_size=safe_limit,
                sort_by="decision_date",
                sort_dir="desc",
            )
            if search_result.items:
                rows = search_result.items
                query_used = candidate
                break
        if rows:
            break

    db.execute(
        delete(CaseLawPrecedentGroup).where(
            CaseLawPrecedentGroup.user_id == user_id,
            CaseLawPrecedentGroup.intake_id == intake.id,
        )
    )
    db.flush()

    if not rows:
        db.commit()
        return [], [], query_used

    buckets: dict[str, list[Any]] = {
        "winning_pattern": [],
        "losing_pattern": [],
        "neutral_pattern": [],
        "emerging_pattern": [],
    }
    refs: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        pattern_type = _bucket_case_law_pattern(row.summary or "", row.decision_date)
        buckets[pattern_type].append(row)
        refs.append(
            {
                "id": row.id,
                "source": row.source,
                "decision_id": row.decision_id,
                "case_number": row.case_number,
                "court_name": row.court_name,
                "decision_date": row.decision_date.isoformat() if row.decision_date else None,
                "summary": row.summary,
                "pattern_type": pattern_type,
                "relevance_score": round(max(0.1, 1.0 - (index - 1) * 0.06), 2),
            }
        )

    groups: list[CaseLawPrecedentGroup] = []
    for pattern_type, items in buckets.items():
        if not items:
            continue
        group = CaseLawPrecedentGroup(
            user_id=user_id,
            intake_id=intake.id,
            pattern_type=pattern_type,
            pattern_description=f"Pattern group {pattern_type} for query: {query_used}",
            precedent_ids=[item.id for item in items],
            precedent_count=len(items),
            pattern_strength=round(min(0.95, 0.45 + len(items) * 0.07), 2),
            counter_arguments=[
                "The opponent may challenge service, causation, or the factual record.",
                "The opponent may argue that the pleaded route or timing is defective.",
            ],
            mitigation_strategy="Tighten the factual record, service trail, and procedural framing before filing.",
            strategic_advantage="The precedent set is segmented into winning, losing, neutral, and emerging patterns.",
            vulnerability_to_appeal="Medium. Keep every core proposition anchored in the record and authorities.",
        )
        db.add(group)
        groups.append(group)

    db.commit()
    for row in groups:
        db.refresh(row)
    return groups, refs, query_used


async def build_strategy_blueprint(
    db: Session,
    *,
    user_id: str,
    intake: DocumentAnalysisIntake,
    precedent_groups: list[CaseLawPrecedentGroup],
    regenerate: bool = True,
) -> LegalStrategyBlueprint:
    if not _is_uk_jurisdiction(intake.jurisdiction):
        # We call the UA version defined in this file at 708
        return await build_strategy_blueprint_ua(
            db,
            user_id=user_id,
            intake=intake,
            precedent_groups=precedent_groups,
            regenerate=regenerate,
        )

    if regenerate:
        db.execute(
            delete(LegalStrategyBlueprint).where(
                LegalStrategyBlueprint.user_id == user_id,
                LegalStrategyBlueprint.intake_id == intake.id,
            )
        )
        db.flush()

    winning_group = next((item for item in precedent_groups if item.pattern_type == "winning_pattern"), None)
    winning_strength = float(winning_group.pattern_strength or 0.0) if winning_group else 0.0
    high_risk = any(
        str(value or "").lower() in {"high", "critical"}
        for value in (intake.risk_level_legal, intake.risk_level_procedural, intake.risk_level_financial)
    )
    base_win = 0.58 + winning_strength * 0.24 - (0.14 if high_risk else 0.0) - (0.08 if not precedent_groups else 0.0)
    base_win = max(0.12, min(base_win, 0.83))

    immediate_actions = [
        {
            "action": "Close the core evidence gaps on liability, quantum, and service.",
            "deadline": (date.today() + timedelta(days=3)).isoformat(),
            "rationale": "The next filing is only as strong as the evidence chain behind the core facts.",
            "evidence_to_collect": ["contract or facility documents", "payments or account records", "service and correspondence trail"],
        },
        {
            "action": "Prepare a counter-argument map for the opponent's likely procedural and factual objections.",
            "deadline": (date.today() + timedelta(days=5)).isoformat(),
            "rationale": "A pre-emptive response plan improves the resilience of the next filing or response.",
            "evidence_to_collect": ["procedural chronology", "service evidence", "supporting authorities"],
        },
    ]
    critical_deadlines = [
        {
            "event": "Update the filing bundle and evidence pack",
            "due_date": (date.today() + timedelta(days=5)).isoformat(),
            "risk_if_missed": "A weak or incomplete record can reduce settlement leverage and filing quality.",
        }
    ]
    if intake.deadline_from_document is not None:
        immediate_actions.insert(
            0,
            {
                "action": "Control the filing or response deadline identified in the source document.",
                "deadline": intake.deadline_from_document if isinstance(intake.deadline_from_document, str) else intake.deadline_from_document.isoformat(),
                "rationale": "The procedural deadline should drive sequencing and drafting priority.",
                "evidence_to_collect": ["proof of service", "document metadata", "deadline wording from the source document"],
            },
        )
        critical_deadlines.insert(
            0,
            {
                "event": "Source-document procedural deadline",
                "due_date": intake.deadline_from_document if isinstance(intake.deadline_from_document, str) else intake.deadline_from_document.isoformat(),
                "risk_if_missed": "Late action may require relief, extension, or a different procedural route.",
            },
        )

    confidence_rationale = "Scoring is based on the intake risk profile and the strength of the available precedent patterns."
    if not precedent_groups:
        confidence_rationale += " Precedent coverage is limited, so human review is recommended before filing."

    procedural_roadmap = [
        {
            "step": 1,
            "legal_action": "Validate jurisdiction and formalize the procedural position.",
            "expected_outcome": "Procedural package ready for filing or service.",
            "pivot_if_lost": "Immediate correction of defects and re-submission.",
        },
        {
            "step": 2,
            "legal_action": "File the claim/application with procedural motions.",
            "expected_outcome": "Proceedings opened and dispute parameters fixed.",
            "pivot_if_lost": "Appellate or alternative procedural route.",
        },
    ]
    evidence_strategy = [
        {
            "phase": "Pleading / Pre-filing",
            "evidence_type": "Core liability and service documents",
            "admissibility": "high",
            "impact": "Establishes the primary factual record.",
        },
        {
            "phase": "Hearing / Trial",
            "evidence_type": "Authorities and witness testimony",
            "admissibility": "medium",
            "impact": "Defends the position against technical challenge.",
        },
    ]

    # Call SWOT Agent for deep analysis
    swot_payload = {
        "strengths": ["Strong fact summary from intake", "Solid procedural alignment"],
        "weaknesses": ["Evidence gaps detected in initial scan", "Tight deadlines"],
        "opportunities": ["Leverage recent supreme court precedents", "Procedural preemption"],
        "threats": ["Counter-arguments on admissibility", "Appeal risks"],
        "win_probability": round(base_win, 2)
    }
    
    try:
        intake_dict = {
            "classified_type": intake.classified_type,
            "subject_matter": intake.subject_matter,
            "risk_level_legal": intake.risk_level_legal,
            "detected_issues": intake.detected_issues,
            "raw_text_preview": intake.raw_text_preview,
            "financial_exposure_amount": float(intake.financial_exposure_amount or 0),
            "deadline_from_document": str(intake.deadline_from_document) if intake.deadline_from_document else None
        }
        groups_dict = [
            {
                "pattern_type": pg.pattern_type,
                "pattern_description": pg.pattern_description,
                "pattern_strength": pg.pattern_strength
            }
            for pg in precedent_groups
        ]
        ai_swot, _ = await run_swot_agent(intake=intake_dict, precedent_groups=groups_dict)
        if ai_swot:
            swot_payload = ai_swot
    except Exception as e:
        print(f"SWOT Agent failed: {e}")

    risk_heat_map = [
        {
            "scenario": "Positive procedural outcome",
            "likelihood_pct": round(float(swot_payload.get("win_probability", 0.6)) * 100, 1),
            "consequences": "Matter proceeds on the strongest procedural footing.",
            "mitigation": "Keep the record clean and focused on key authorities.",
        },
        {
            "scenario": "Partial success / Directions",
            "likelihood_pct": round((1 - float(swot_payload.get("win_probability", 0.6))) * 45, 1),
            "consequences": "Only part of the route survives primary scrutiny.",
            "mitigation": "Narrow the issues and optimize for the most defensible route.",
        },
        {
            "scenario": "Adverse procedural ruling",
            "likelihood_pct": round((1 - float(swot_payload.get("win_probability", 0.6))) * 35, 1),
            "consequences": "Matter requires appeal or settlement pivot.",
            "mitigation": "Prepare fallback routing and settlement parameters.",
        },
    ]

    # Final construction
    wp = swot_payload.get("win_probability")
    if wp is None:
        wp = base_win
    
    blueprint = LegalStrategyBlueprint(
        user_id=user_id,
        intake_id=intake.id,
        precedent_group_id=precedent_groups[0].id if precedent_groups else None,
        immediate_actions=immediate_actions,
        procedural_roadmap=procedural_roadmap,
        evidence_strategy=evidence_strategy,
        negotiation_playbook=[
            {
                "counterparty_offer": "Partial concession without costs or timetable certainty",
                "our_counter": "Accept only with timetable discipline, cost clarity, and defined next steps.",
                "reasoning": "A weakly framed concession can create more procedural risk than value.",
            }
        ],
        risk_heat_map=risk_heat_map,
        critical_deadlines=critical_deadlines,
        swot_analysis=swot_payload or {},
        win_probability=float(wp),
        financial_strategy=swot_payload.get("financial_strategy"),
        timeline_projection=swot_payload.get("timeline_projection"),
        penalty_forecast=swot_payload.get("penalty_forecast"),
        confidence_score=round(float(wp), 2),
        confidence_rationale=confidence_rationale,
        recommended_next_steps=(
            "1) Опрацюйте слабкі сторони згідно зі SWOT-аналізом. "
            "2) Підготуйте доказову базу для закриття виявлених прогалин. "
            "3) Оцініть фінансову доцільність згідно з розрахунками витрат."
        ),
    )
    # Ensure SWOT keys are present for frontend
    if isinstance(blueprint.swot_analysis, dict):
        blueprint.swot_analysis = {
            "strengths": blueprint.swot_analysis.get("strengths") or [],
            "weaknesses": blueprint.swot_analysis.get("weaknesses") or [],
            "opportunities": blueprint.swot_analysis.get("opportunities") or [],
            "threats": blueprint.swot_analysis.get("threats") or []
        }

    db.add(blueprint)
    db.commit()
    db.refresh(blueprint)
    return blueprint
