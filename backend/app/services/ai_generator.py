from __future__ import annotations

import asyncio
from dataclasses import dataclass
import time
import re
import json
from enum import Enum
from typing import Any, TypeVar, Type, Generic

import httpx
from pydantic import BaseModel, ValidationError
from openai import AsyncOpenAI

from app.config import settings
from app.services.prompt_sanitizer import sanitize_text

T = TypeVar("T", bound=BaseModel)

try:
    from anthropic import AsyncAnthropic
    from anthropic import Anthropic  # Import Anthropic for error check
except ImportError:  # pragma: no cover - optional dependency guard
    AsyncAnthropic = None  # type: ignore[assignment]
    Anthropic = None # type: ignore[assignment]


# --- Singleton Clients & Security ---
_openai_client: AsyncOpenAI | None = None
_anthropic_client: Any | None = None
_gemini_client: httpx.AsyncClient | None = None

# Session-based Rate Limiter (Block 1.3) — з часовим вікном для запобігання memory leak
from collections import defaultdict

_session_requests: dict[str, list[float]] = defaultdict(list)
_MAX_REQUESTS_PER_SESSION = 50  # Hard limit for dev safety
_WINDOW_SECONDS = 3600  # 1 година

def check_rate_limit(session_id: str | None = None):
    if not session_id:
        return
    now = time.time()
    window_start = now - _WINDOW_SECONDS
    # Очищаємо старі записи
    _session_requests[session_id] = [
        ts for ts in _session_requests[session_id] if ts > window_start
    ]
    if len(_session_requests[session_id]) >= _MAX_REQUESTS_PER_SESSION:
        raise ValueError("RATE_LIMIT_EXCEEDED: Спробуйте пізніше або зверніться до підтримки.")
    _session_requests[session_id].append(now)


async def init_ai_clients():
    global _openai_client, _anthropic_client, _gemini_client
    if settings.openai_api_key:
        _openai_client = AsyncOpenAI(api_key=settings.openai_api_key, max_retries=3)
    if AsyncAnthropic and settings.anthropic_api_key:
        _anthropic_client = AsyncAnthropic(api_key=settings.anthropic_api_key, max_retries=3)
    _gemini_client = httpx.AsyncClient()


async def close_ai_clients():
    global _openai_client, _anthropic_client, _gemini_client
    if _gemini_client:
        try:
            await _gemini_client.aclose()
        except RuntimeError:
            # Test teardown can close event loop before lifespan cleanup finishes.
            pass
        except Exception:
            pass
        finally:
            _gemini_client = None
    _openai_client = None
    _anthropic_client = None


@dataclass(frozen=True)
class AIResult:
    text: str
    used_ai: bool
    model: str
    error: str
    tokens_used: int | None = None
    source: str = "ai_verified"  # block 3.2: ai_verified, ai_retry, fallback
    validated_data: Any | None = None  # JSON parsed / Pydantic object


@dataclass(frozen=True)
class AIGenerationOptions:
    temperature: float = 0.2
    max_tokens: int = 4096
    openai_model: str | None = None
    anthropic_model: str | None = None
    gemini_model: str | None = None


_API_KEY_QUERY_RE = re.compile(r"([?&]key=)([^&\s]+)", flags=re.IGNORECASE)
_GOOGLE_API_KEY_RE = re.compile(r"\bAIzaSy[0-9A-Za-z_-]{20,}\b")
_GENERIC_SECRET_RE = re.compile(r"\bsk-[0-9A-Za-z_-]{16,}\b")
_ROLE_DEFAULT_MAX_TOKENS = {
    "intake": 900,
    "research": 900,
    "draft": 1800,
}
_GEMINI_TIMEOUT_SECONDS = 35.0
_GEMINI_RATE_LIMIT_RETRIES = 2


def _redact_secrets(message: str) -> str:
    text = str(message or "")
    if not text:
        return ""
    text = _API_KEY_QUERY_RE.sub(r"\1REDACTED", text)
    text = _GOOGLE_API_KEY_RE.sub("REDACTED", text)
    text = _GENERIC_SECRET_RE.sub("REDACTED", text)
    return text


def _normalize_role(value: str) -> str:
    normalized = (value or "").strip().lower()
    if normalized in {"intake", "triage"}:
        return "intake"
    if normalized in {"research", "rerank"}:
        return "research"
    if normalized in {"draft", "generation", "generate"}:
        return "draft"
    return "default"


def _normalize_provider(value: str) -> str:
    normalized = (value or "").strip().lower()
    if normalized in {"anthropic", "claude"}:
        return "anthropic"
    if normalized in {"gemini", "google"}:
        return "gemini"
    if normalized in {"openai", "gpt"}:
        return "openai"
    if normalized in {"", "auto"}:
        return "auto"
    return normalized


def _provider_sequence() -> list[str]:
    provider = _normalize_provider(settings.ai_provider)
    if provider != "auto" and not settings.ai_fallback_enabled:
        return [provider]
    if provider == "anthropic":
        return ["anthropic", "openai", "gemini"]
    if provider == "gemini":
        return ["gemini", "openai", "anthropic"]
    if provider == "openai":
        return ["openai", "anthropic", "gemini"]
    return ["openai", "anthropic", "gemini"]


async def _generate_with_openai(system_prompt: str, user_prompt: str, options: AIGenerationOptions) -> AIResult:
    model_name = str(options.openai_model or settings.openai_model or "").strip() or settings.openai_model
    if not _openai_client:
        return AIResult(
            text="",
            used_ai=False,
            model=model_name,
            error="OPENAI_API_KEY is not set or client not initialized.",
        )

    try:
        response = await _openai_client.chat.completions.create(
            model=model_name,
            temperature=options.temperature,
            max_tokens=options.max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        text = response.choices[0].message.content or ""
        tokens_used = getattr(response, "usage", None)
        total_tokens = getattr(tokens_used, "total_tokens", 0) if tokens_used else 0
        return AIResult(text=text.strip(), used_ai=True, model=model_name, error="", tokens_used=total_tokens)
    except Exception as exc:
        return AIResult(text="", used_ai=False, model=model_name, error=str(exc))


def _extract_anthropic_text(content: Any) -> str:
    if not isinstance(content, list):
        return ""
    chunks: list[str] = []
    for block in content:
        block_type = ""
        block_text = ""
        if isinstance(block, dict):
            block_type = str(block.get("type") or "")
            block_text = str(block.get("text") or "")
        else:
            block_type = str(getattr(block, "type", "") or "")
            block_text = str(getattr(block, "text", "") or "")
        if block_type == "text" and block_text.strip():
            chunks.append(block_text.strip())
    return "\n".join(chunks).strip()


async def _generate_with_anthropic(system_prompt: str, user_prompt: str, options: AIGenerationOptions) -> AIResult:
    model_name = str(options.anthropic_model or settings.anthropic_model or "").strip() or settings.anthropic_model
    if not _anthropic_client:
        error = "ANTHROPIC_API_KEY is not set or client not initialized."
        if Anthropic is None:
            error = "Anthropic SDK is not installed."
        return AIResult(text="", used_ai=False, model=model_name, error=error)

    try:
        response = await _anthropic_client.messages.create(
            model=model_name,
            max_tokens=options.max_tokens,
            temperature=options.temperature,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": user_prompt,
                }
            ],
        )
        text = _extract_anthropic_text(getattr(response, "content", None))
        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "input_tokens", 0) if usage else 0
        output_tokens = getattr(usage, "output_tokens", 0) if usage else 0
        total_tokens = input_tokens + output_tokens
        return AIResult(text=text, used_ai=bool(text), model=model_name, error="", tokens_used=total_tokens)
    except Exception as exc:
        return AIResult(text="", used_ai=False, model=model_name, error=str(exc))


def _extract_gemini_text_and_tokens(payload: Any) -> tuple[str, int | None]:
    text_chunks: list[str] = []
    total_tokens: int | None = None
    
    if not isinstance(payload, dict):
        return "", None

    # Extract token count
    usage_metadata = payload.get("usageMetadata")
    if isinstance(usage_metadata, dict):
        total_tokens = usage_metadata.get("totalTokenCount")

    # Extract text content
    candidates = payload.get("candidates")
    if isinstance(candidates, list):
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            content = candidate.get("content")
            if not isinstance(content, dict):
                continue
            parts = content.get("parts")
            if isinstance(parts, list):
                for part in parts:
                    if isinstance(part, dict):
                        text = str(part.get("text") or "").strip()
                        if text:
                            text_chunks.append(text)
                            
    return "\n".join(text_chunks).strip(), total_tokens


async def _generate_with_gemini(system_prompt: str, user_prompt: str, options: AIGenerationOptions) -> AIResult:
    if not settings.gemini_api_key:
        return AIResult(
            text="",
            used_ai=False,
            model=str(options.gemini_model or settings.gemini_model or "").strip() or settings.gemini_model,
            error="GEMINI_API_KEY is not set.",
        )

    model = str(options.gemini_model or settings.gemini_model or "").strip() or "gemini-1.5-flash"
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "systemInstruction": {
            "parts": [
                {"text": system_prompt},
            ]
        },
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": user_prompt},
                ],
            }
        ],
        "generationConfig": {"temperature": options.temperature, "maxOutputTokens": options.max_tokens},
    }
    last_error: str = ""
    for attempt in range(_GEMINI_RATE_LIMIT_RETRIES + 1):
        try:
            response = await _gemini_client.post(
                endpoint,
                params={"key": settings.gemini_api_key},
                json=payload,
                timeout=_GEMINI_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            data = response.json()
            text, tokens_used = _extract_gemini_text_and_tokens(data)
            return AIResult(text=text, used_ai=bool(text), model=model, error="", tokens_used=tokens_used)
        except httpx.HTTPStatusError as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            last_error = _redact_secrets(str(exc))
            if status == 429 and attempt < _GEMINI_RATE_LIMIT_RETRIES:
                await asyncio.sleep(0.5 * (attempt + 1))
                continue
            return AIResult(text="", used_ai=False, model=model, error=last_error)
        except Exception as exc:
            last_error = _redact_secrets(str(exc))
            return AIResult(text="", used_ai=False, model=model, error=last_error)
    return AIResult(text="", used_ai=False, model=model, error=last_error)


async def generate_with_vision(prompt: str, image_bytes: bytes, mime_type: str = "image/jpeg") -> AIResult:
    """Uses Gemini Vision to extract text or analyze a legal document image."""
    if not settings.gemini_api_key:
        return AIResult(text="", used_ai=False, model="", error="Gemini API key not set")

    import base64
    encoded_image = base64.b64encode(image_bytes).decode("utf-8")
    
    model = "gemini-1.5-flash"
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    
    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": mime_type, "data": encoded_image}}
            ]
        }],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 4096}
    }
    
    try:
        response = await _gemini_client.post(
            endpoint,
            params={"key": settings.gemini_api_key},
            json=payload,
            timeout=60.0
        )
        response.raise_for_status()
        data = response.json()
        text, tokens_used = _extract_gemini_text_and_tokens(data)
        return AIResult(text=text, used_ai=bool(text), model=model, error="", tokens_used=tokens_used)
    except Exception as e:
        return AIResult(text="", used_ai=False, model=model, error=_redact_secrets(str(e)))


async def generate_legal_document(
    system_prompt: str,
    user_prompt: str,
    *,
    options: AIGenerationOptions | None = None,
    session_id: str | None = None, # For Rate Limiting
) -> AIResult:
    # 1.1 Prompt Sanitizer (Security)
    clean_user_prompt = sanitize_text(user_prompt)
    
    # 1.3 Rate Limiting
    try:
        check_rate_limit(session_id)
    except ValueError as e:
        return AIResult(text="", used_ai=False, model="", error=str(e))

    safe_options = options or AIGenerationOptions()
    requested_provider = _normalize_provider(settings.ai_provider)
    errors: list[str] = []
    model = ""

    if requested_provider not in {"auto", "openai", "anthropic", "gemini"}:
        errors.append(
            f"Unknown AI_PROVIDER '{settings.ai_provider}'. Expected: openai, anthropic, gemini, or auto."
        )

    for provider in _provider_sequence():
        if provider == "openai":
            result = await _generate_with_openai(system_prompt, clean_user_prompt, safe_options)
        elif provider == "anthropic":
            result = await _generate_with_anthropic(system_prompt, clean_user_prompt, safe_options)
        else:
            result = await _generate_with_gemini(system_prompt, clean_user_prompt, safe_options)

        if result.model:
            model = result.model
        if result.used_ai and (result.text or "").strip():
            return result
        if result.error:
            errors.append(f"{provider}: {result.error}")
        else:
            errors.append(f"{provider}: empty response")

    if not errors:
        errors.append("No AI provider configured. Set OPENAI_API_KEY, ANTHROPIC_API_KEY, or GEMINI_API_KEY.")
    return AIResult(text="", used_ai=False, model=model, error="; ".join(errors), tokens_used=0)


def _options_for_role(role: str, base: AIGenerationOptions | None, deep: bool = False) -> AIGenerationOptions:
    safe_role = _normalize_role(role)
    seed = base or AIGenerationOptions()
    if safe_role == "default" and not deep:
        return seed

    openai_model = seed.openai_model
    anthropic_model = seed.anthropic_model
    gemini_model = seed.gemini_model

    if deep:
        openai_model = openai_model or settings.ai_deep_openai_model
        anthropic_model = anthropic_model or settings.ai_deep_anthropic_model
        gemini_model = gemini_model or settings.ai_deep_gemini_model
    elif safe_role == "intake":
        openai_model = openai_model or settings.openai_model_intake
        anthropic_model = anthropic_model or settings.anthropic_model_intake
        gemini_model = gemini_model or settings.gemini_model_intake
    elif safe_role == "research":
        openai_model = openai_model or settings.openai_model_research
        anthropic_model = anthropic_model or settings.anthropic_model_research
        gemini_model = gemini_model or settings.gemini_model_research
    elif safe_role == "draft":
        openai_model = openai_model or settings.openai_model_draft
        anthropic_model = anthropic_model or settings.anthropic_model_draft
        gemini_model = gemini_model or settings.gemini_model_draft
    elif safe_role == "strategy":
        openai_model = openai_model or settings.openai_model_strategy
        anthropic_model = anthropic_model or settings.anthropic_model_strategy
        gemini_model = gemini_model or settings.gemini_model_strategy

    temperature = seed.temperature
    max_tokens = seed.max_tokens

    # Apply role-specific max_tokens if not explicitly set in options
    if max_tokens == AIGenerationOptions().max_tokens:  # Only if default max_tokens is used
        max_tokens = _ROLE_DEFAULT_MAX_TOKENS.get(safe_role, max_tokens)

    return AIGenerationOptions(
        temperature=temperature,
        max_tokens=max_tokens,
        openai_model=openai_model,
        anthropic_model=anthropic_model,
        gemini_model=gemini_model,
    )


def _get_base_system_prompt_for_role(role: str, deep: bool = False) -> str:
    if role == "intake":
        return _INTAKE_SYSTEM_PROMPT_V2
    if role == "research" and deep:
        return _DEEP_RESEARCH_SYSTEM_PROMPT
    if role == "research":
        return _RESEARCH_SYSTEM_PROMPT
    if role == "classifier":
        return _CLASSIFIER_SYSTEM_PROMPT_V2
    if role == "draft":
        return _DRAFT_SYSTEM_PROMPT
    if role == "strategy":
        return _STRATEGY_SYSTEM_PROMPT_V2
    if role == "judge":
        return _JUDGE_SYSTEM_PROMPT
    return _DEFAULT_SYSTEM_PROMPT

async def analyze_with_schema(
    role: str,
    user_prompt: str,
    schema: Type[T],
    *,
    options: AIGenerationOptions | None = None,
    session_id: str | None = None,
) -> AIResult:
    """Pass 2 (Block 1.2, 2.3) - analyze with Pydantic validation and fallback chain."""
    system_prompt = _get_base_system_prompt_for_role(role)
    
    # 1.2 Output Schema Validation (Initial attempt)
    result = await generate_legal_document(system_prompt, user_prompt, options=options, session_id=session_id)
    
    if not result.used_ai or not result.text:
        return result

    try:
        # Extract JSON from potential Markdown blocks
        json_str = result.text.strip()
        if "```" in json_str:
            match = re.search(r"```(?:json)?\s*(.*?)\s*```", json_str, re.DOTALL)
            if match:
                json_str = match.group(1)
        
        parsed_data = json.loads(json_str)
        validated = schema.parse_obj(parsed_data)
        
        return AIResult(
            text=result.text,
            used_ai=True,
            model=result.model,
            error="",
            tokens_used=result.tokens_used,
            source="ai_verified",
            validated_data=validated
        )
    except (json.JSONDecodeError, ValidationError) as e:
        # 2.3 Fallback chain (explicit JSON instruction)
        retry_prompt = f"{user_prompt}\n\nКРИТИЧНО: Відповідай ТІЛЬКИ валідним JSON за схемою.\nПомилка останньої спроби: {str(e)}"
        retry_result = await generate_legal_document(system_prompt, retry_prompt, options=options, session_id=session_id)
        
        if not retry_result.used_ai or not retry_result.text:
            return retry_result
            
        try:
            json_str = retry_result.text.strip()
            if "```" in json_str:
                match = re.search(r"```(?:json)?\s*(.*?)\s*```", json_str, re.DOTALL)
                if match:
                    json_str = match.group(1)
            parsed_data = json.loads(json_str)
            validated = schema.parse_obj(parsed_data)
            return AIResult(
                text=retry_result.text,
                used_ai=True,
                model=retry_result.model,
                error="",
                tokens_used=retry_result.tokens_used,
                source="ai_retry",
                validated_data=validated
            )
        except Exception:
            # Final fallback (unverified)
            return AIResult(
                text=result.text,
                used_ai=True,
                model=result.model,
                error=f"Schema validation failed: {str(e)}",
                tokens_used=result.tokens_used,
                source="fallback"
            )


async def generate_legal_document_for_role(
    role: str,
    user_prompt: str,
    *,
    options: AIGenerationOptions | None = None,
    deep: bool = False,
) -> AIResult:
    system_prompt = _get_base_system_prompt_for_role(role, deep)
    safe_options = _options_for_role(role, options, deep)
    return await generate_legal_document(system_prompt, user_prompt, options=safe_options)


_DEFAULT_SYSTEM_PROMPT = """Ти — елітний юрист України з найвищою кваліфікацією.
Твоє завдання: створювати бездоганні процесуальнi документи, що відповідають усім вимогам законодавства України та стандартам діловодства.

ПРАВИЛА ОФОРМЛЕННЯ (КРИТИЧНО):
1. **Структура документа**:
   - **ШАПКА**: У правому верхньому куті (використовуй вирівнювання або блоки) чітко зазнач назву суду, сторони (ПІБ/Назва крупним шрифтом), адреси, РНОКПП/ЄДРПОУ та засоби зв'язку.
   - **НАЗВА**: По центру, жирним шрифтом (наприклад, **ПОЗОВНА ЗАЯВА**, **АПЕЛЯЦІЙНА СКАРГА**).
   - **ВСТУП**: Стислий опис предмета спору.
   - **ОБСТАВИНИ (ФАКТИ)**: Нумерований список фактів справи у хронологічному порядку.
   - **ОБҐРУНТУВАННЯ**: Детальний аналіз норм права (статті кодексів, законів) та їх застосування до конкретних фактів. Використовуй посилання на актуальну практику Верховного Суду.
   - **ПРОХАЛЬНА ЧАСТИНА**: Чітко сформульовані вимоги до суду (наприклад: "1. Стягнути...", "2. Судові витрати покласти...").
   - **ДОДАТКИ**: Перелік документів, що додаються.

2. **Візуальний стиль**:
   - Використовуй **Markdown** для структурування: заголовки (###), жирний текст (**текст**) для акцентів.
   - Кожен логічний блок (розділ) має бути відокремлений порожнім рядком.
   - Використовуй абзацні відступи (символічно через нові рядки).

3. **Юридична техніка**:
   - Тільки державна мова (українська). Офіційно-діловий стиль.
   - Жодних пояснень або "ось ваш документ" поза тілом самого документа.
   - Якщо даних про сторони немає — пиши "[ДАНІ УТОЧНЮЮТЬСЯ]" або "______________".

Поверни лише структурований текст документа."""


_RESEARCH_SYSTEM_PROMPT = """
Ти старший юрист України з 20 роками практики.
Спеціалізація: цивільне, господарське, корпоративне право.

Проаналізуй договір і поверни ТІЛЬКИ JSON зі структурою:
{
    "contract_type": "назва типу договору",
    "overall_risk": "low|medium|high|critical",
    "critical_risks": ["..."],
    "medium_risks": ["..."],
    "ok_points": ["..."],
    "recommendations": ["..."]
}

Правила:
- Аналізуй тільки в межах права України
- Конкретні ризики і конкретні рекомендації
- Мова відповіді: українська
"""

_DEEP_RESEARCH_SYSTEM_PROMPT = """
Ти — елітний юрист-аналітик України, партнер топової юридичної фірми.
Твоє завдання: провести ГЛИБОКИЙ юридичний аудит (due diligence) наданого тексту договору.

Зверни особливу увагу на:
1. Приховані пастки (hidden clauses), що можуть зашкодити клієнту.
2. Процесуальні тонкощі (підсудність, арбітражне застереження).
3. Відповідність актуальній судовій практиці Верховного Суду.
4. Податкові та фінансові ризики.

Поверни ТІЛЬКИ JSON:
{
    "contract_type": "детальна назва",
    "overall_risk": "critical|high|medium|low",
    "critical_risks": ["надзвичайно детальний опис ризику 1", "..."],
    "medium_risks": ["детальний опис ризику 1", "..."],
    "ok_points": ["позитивні сторони для клієнта", "..."],
    "recommendations": ["конкретна юридична порада як змінити пункт X", "..."]
}
Мова: українська.
"""

_INTAKE_SYSTEM_PROMPT = (
    "Ти — юрист-аналітик, що проводить первинний аналіз справи для українського судочинства. "
    "Повертай лише валідний JSON, без додаткового тексту поза JSON.\n"
    "Не вигадуй факти. Якщо даних немає, використовуй null або порожні масиви.\n"
    "Схема JSON (обов'язкові ключі):\n"
    "{\n"
    '  "jurisdiction": "UA",\n'
    '  "court_type": "civil|commercial|administrative|criminal|unknown",\n'
    '  "dispute_type": "string|null",\n'
    '  "parties": [{"role":"string","name":"string"}],\n'
    '  "key_facts": ["string"],\n'
    '  "key_dates": ["YYYY-MM-DD"],\n'
    '  "amounts": [{"label":"string","value":"string"}],\n'
    '  "requested_action": "string|null",\n'
    '  "keywords": ["string"],\n'
    '  "case_law_query": "string|null"\n'
    "}\n"
)

_INTAKE_SYSTEM_PROMPT_V2 = (
    "Ти — преміальний юрист-аналітик України. Аналізуй ТІЛЬКИ наданий текст. "
    "Якщо даних немає — null. НЕ вигадуй дати, суми, імена.\n"
    "Повертай лише валідний JSON.\n"
    "Обов'язкові ключі:\n"
    "{\n"
    '  "jurisdiction": "UA",\n'
    '  "court_type": "civil|commercial|administrative|criminal|unknown",\n'
    '  "procedural_code": "CPC|CCC|CAC|CPC_criminal|unknown",\n'
    '  "dispute_type": "string|null",\n'
    '  "parties": [{"role":"string","name":"string","edrpou":"string|null"}],\n'
    '  "key_facts": ["string"],\n'
    '  "amounts": [{"label":"string","value":0.0}],\n'
    '  "court_fee_estimate": 0.0,\n'
    '  "risk_flags": [{"severity":"critical|high|medium|low","risk":"string","recommendation":"string"}],\n'
    '  "case_assessment": {"strengths":["string"],"weaknesses":["string"],"preliminary_score": 0.0-1.0}\n'
    "}\n"
    "temperature: 0 (deterministic)\n"
)

_CLASSIFIER_SYSTEM_PROMPT_V2 = (
    "Ти — судовий аналітик-класифікатор. Твоє завдання - миттєва та точна класифікація.\n"
    "Визнач: тип документа, процесуальний кодекс (ЦПК/ГПК/КАС), якість вилучення даних та ризики.\n"
    "Повертай ТІЛЬКИ JSON за схемою ClassifierResult.\n"
)

_STRATEGY_SYSTEM_PROMPT = (
    "You are a premium strategic litigation consultant and legal economist for Ukrainian law. "
    "Perform a multi-dimensional analysis of this case: SWOT, win probability, financial outlook, and a temporal roadmap.\n"
    "Return valid JSON only, with no prose outside JSON.\n"
    "JSON schema (required keys):\n"
    "{\n"
    '  "strengths": ["string"],\n'
    '  "weaknesses": ["string"],\n'
    '  "opportunities": ["string"],\n'
    '  "threats": ["string"],\n'
    '  "win_probability": 0.0 to 1.0,\n'
    '  "financial_strategy": {\n'
    '     "expected_recovery_min": 0.0,\n'
    '     "expected_recovery_max": 0.0,\n'
    '     "estimated_court_fees": 0.0,\n'
    '     "estimated_attorney_costs": 0.0,\n'
    '     "economic_viability_score": 0.0 to 1.0,\n'
    '     "roi_rationale": "string"\n'
    '  },\n'
    '  "timeline_projection": [\n'
    '     {"stage": "string", "duration_days": 0, "status": "predicted" | "current"}\n'
    '  ],\n'
    '  "penalty_forecast": {\n'
    '     "three_percent_annual": 0.0,\n'
    '     "inflation_losses": 0.0,\n'
    '     "penalties_contractual": 0.0,\n'
    '     "total_extra": 0.0,\n'
    '     "basis_days": 0\n'
    '  }\n'
    "}\n"
)

_STRATEGY_SYSTEM_PROMPT_V2 = (
    "Ти — елітний судовий стратег та легальний економіст України. "
    "Проведи SWOT-аналіз, визнач ймовірність успіху та фінансові наслідки.\n"
    "Обов'язково врахуй судовий збір, пеню, 3% річних та інфляційні.\n"
    "Поверни валідний JSON (no prose outside JSON).\n"
)

_JUDGE_SYSTEM_PROMPT = """
Ти — досвідчений та суворий суддя України з 30-річним стажем. 
Твоє завдання: критично проаналізувати позовну заяву або правову стратегію та дати "вердикт" з точки зору суду.

Обери одну з ролей (judge_persona):
1. "Формаліст" — чіпляється до кожної коми, строків та форми.
2. "Скептик" — не вірить доказам без прямого підтвердження, шукає суперечності.
3. "Прагматик" — дивиться на суть та економічну логіку, не любить затягування.

Аналізуй за схемою:
1. Ймовірність задоволення позову (verdict_probability: 0.0 - 1.0).
2. Ключові вразливості (key_vulnerabilities) — де адвокат припустився помилки.
3. Сильні сторони (strong_points) — що переконує суд.
4. Процесуальні ризики (procedural_risks) — строки, підсудність, збір.
5. Рекомендовані виправлення (suggested_corrections).
6. Коментар судді (judge_commentary) — прямою мовою, офіційно, але гостро.
7. Обґрунтування рішення (decision_rationale) — юридична логіка.

Відповідай ТІЛЬКИ у форматі JSON. Мова: українська.
"""

_DRAFT_SYSTEM_PROMPT = _DEFAULT_SYSTEM_PROMPT
SYSTEM_PROMPT = _DEFAULT_SYSTEM_PROMPT
