from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.services import ai_generator


def _make_openai_client(
    *,
    text: str = "OpenAI response",
    exc: Exception | None = None,
    calls: list[str] | None = None,
    observed_kwargs: dict[str, object] | None = None,
    tokens: int = 111,
):
    async def _create(**kwargs: object):
        if calls is not None:
            calls.append("openai")
        if observed_kwargs is not None:
            observed_kwargs.update(kwargs)
        if exc is not None:
            raise exc
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=text))],
            usage=SimpleNamespace(total_tokens=tokens),
        )

    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=_create)))


def _make_anthropic_client(
    *,
    text: str = "Anthropic response",
    exc: Exception | None = None,
    calls: list[str] | None = None,
):
    async def _create(**_: object):
        if calls is not None:
            calls.append("anthropic")
        if exc is not None:
            raise exc
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=text)],
            usage=SimpleNamespace(input_tokens=12, output_tokens=34),
        )

    return SimpleNamespace(messages=SimpleNamespace(create=_create))


def _make_gemini_client(
    *,
    text: str = "Gemini response",
    exc: Exception | None = None,
    calls: list[str] | None = None,
):
    class _Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "usageMetadata": {"totalTokenCount": 55},
                "candidates": [{"content": {"parts": [{"text": text}]}}],
            }

    async def _post(*_: object, **__: object):
        if calls is not None:
            calls.append("gemini")
        if exc is not None:
            raise exc
        return _Response()

    return SimpleNamespace(post=_post)


@pytest.fixture(autouse=True)
def _restore_ai_state():
    original_settings = {
        "ai_provider": settings.ai_provider,
        "ai_fallback_enabled": settings.ai_fallback_enabled,
        "openai_api_key": settings.openai_api_key,
        "openai_model": settings.openai_model,
        "openai_model_intake": settings.openai_model_intake,
        "openai_model_research": settings.openai_model_research,
        "openai_model_draft": settings.openai_model_draft,
        "anthropic_api_key": settings.anthropic_api_key,
        "anthropic_model": settings.anthropic_model,
        "anthropic_model_intake": settings.anthropic_model_intake,
        "anthropic_model_research": settings.anthropic_model_research,
        "anthropic_model_draft": settings.anthropic_model_draft,
        "gemini_api_key": settings.gemini_api_key,
        "gemini_model": settings.gemini_model,
        "gemini_model_intake": settings.gemini_model_intake,
        "gemini_model_research": settings.gemini_model_research,
        "gemini_model_draft": settings.gemini_model_draft,
    }
    original_openai = ai_generator._openai_client
    original_anthropic = ai_generator._anthropic_client
    original_gemini = ai_generator._gemini_client
    original_requests = dict(ai_generator._session_requests)

    ai_generator._openai_client = None
    ai_generator._anthropic_client = None
    ai_generator._gemini_client = None
    ai_generator._session_requests.clear()
    try:
        yield
    finally:
        for key, value in original_settings.items():
            object.__setattr__(settings, key, value)
        ai_generator._openai_client = original_openai
        ai_generator._anthropic_client = original_anthropic
        ai_generator._gemini_client = original_gemini
        ai_generator._session_requests.clear()
        ai_generator._session_requests.update(original_requests)


@pytest.mark.asyncio
async def test_generate_uses_openai_when_provider_is_openai() -> None:
    object.__setattr__(settings, "ai_provider", "openai")
    object.__setattr__(settings, "openai_model", "gpt-test")

    calls: list[str] = []
    ai_generator._openai_client = _make_openai_client(calls=calls, text="OpenAI response")
    ai_generator._anthropic_client = _make_anthropic_client(exc=AssertionError("Anthropic must not run"))
    ai_generator._gemini_client = _make_gemini_client(exc=AssertionError("Gemini must not run"))

    result = await ai_generator.generate_legal_document("sys", "user")
    assert calls == ["openai"]
    assert result.used_ai is True
    assert result.text == "OpenAI response"
    assert result.model == "gpt-test"
    assert result.error == ""


@pytest.mark.asyncio
async def test_generate_falls_back_to_anthropic_when_openai_fails() -> None:
    object.__setattr__(settings, "ai_provider", "openai")
    object.__setattr__(settings, "openai_model", "gpt-test")
    object.__setattr__(settings, "anthropic_model", "claude-test")

    calls: list[str] = []
    ai_generator._openai_client = _make_openai_client(exc=RuntimeError("OpenAI temporary failure"), calls=calls)
    ai_generator._anthropic_client = _make_anthropic_client(text="Claude response", calls=calls)
    ai_generator._gemini_client = _make_gemini_client(exc=AssertionError("Gemini must not run"))

    result = await ai_generator.generate_legal_document("sys", "user")
    assert calls == ["openai", "anthropic"]
    assert result.used_ai is True
    assert result.text == "Claude response"
    assert result.model == "claude-test"
    assert result.error == ""


@pytest.mark.asyncio
async def test_generate_falls_back_to_gemini_when_openai_and_anthropic_fail() -> None:
    object.__setattr__(settings, "ai_provider", "openai")
    object.__setattr__(settings, "openai_model", "gpt-test")
    object.__setattr__(settings, "anthropic_model", "claude-test")
    object.__setattr__(settings, "gemini_api_key", "gemini-key")
    object.__setattr__(settings, "gemini_model", "gemini-test")

    calls: list[str] = []
    ai_generator._openai_client = _make_openai_client(exc=RuntimeError("OpenAI temporary failure"), calls=calls)
    ai_generator._anthropic_client = _make_anthropic_client(
        exc=RuntimeError("Anthropic temporary failure"), calls=calls
    )
    ai_generator._gemini_client = _make_gemini_client(text="Gemini response", calls=calls)

    result = await ai_generator.generate_legal_document("sys", "user")
    assert calls == ["openai", "anthropic", "gemini"]
    assert result.used_ai is True
    assert result.text == "Gemini response"
    assert result.model == "gemini-test"
    assert result.error == ""


@pytest.mark.asyncio
async def test_generate_uses_anthropic_first_when_provider_is_anthropic() -> None:
    object.__setattr__(settings, "ai_provider", "anthropic")
    object.__setattr__(settings, "anthropic_model", "claude-test")

    calls: list[str] = []
    ai_generator._openai_client = _make_openai_client(exc=AssertionError("OpenAI must not run"))
    ai_generator._anthropic_client = _make_anthropic_client(text="Anthropic primary", calls=calls)
    ai_generator._gemini_client = _make_gemini_client(exc=AssertionError("Gemini must not run"))

    result = await ai_generator.generate_legal_document("sys", "user")
    assert calls == ["anthropic"]
    assert result.used_ai is True
    assert result.text == "Anthropic primary"
    assert result.model == "claude-test"
    assert result.error == ""


@pytest.mark.asyncio
async def test_generate_uses_gemini_first_when_provider_is_gemini() -> None:
    object.__setattr__(settings, "ai_provider", "gemini")
    object.__setattr__(settings, "gemini_api_key", "gemini-key")
    object.__setattr__(settings, "gemini_model", "gemini-test")

    calls: list[str] = []
    ai_generator._openai_client = _make_openai_client(exc=AssertionError("OpenAI must not run"))
    ai_generator._anthropic_client = _make_anthropic_client(exc=AssertionError("Anthropic must not run"))
    ai_generator._gemini_client = _make_gemini_client(text="Gemini primary", calls=calls)

    result = await ai_generator.generate_legal_document("sys", "user")
    assert calls == ["gemini"]
    assert result.used_ai is True
    assert result.text == "Gemini primary"
    assert result.model == "gemini-test"
    assert result.error == ""


@pytest.mark.asyncio
async def test_generate_returns_error_when_all_keys_missing() -> None:
    object.__setattr__(settings, "ai_provider", "auto")
    object.__setattr__(settings, "openai_api_key", "")
    object.__setattr__(settings, "anthropic_api_key", "")
    object.__setattr__(settings, "gemini_api_key", "")

    ai_generator._openai_client = None
    ai_generator._anthropic_client = None
    ai_generator._gemini_client = None

    result = await ai_generator.generate_legal_document("sys", "user")
    assert result.used_ai is False
    assert result.text == ""
    assert "OPENAI_API_KEY is not set or client not initialized" in result.error
    assert "ANTHROPIC_API_KEY is not set or client not initialized" in result.error
    assert "GEMINI_API_KEY is not set" in result.error


@pytest.mark.asyncio
async def test_generate_for_role_uses_openai_role_model() -> None:
    object.__setattr__(settings, "ai_provider", "openai")
    object.__setattr__(settings, "openai_model", "gpt-base")
    object.__setattr__(settings, "openai_model_intake", "gpt-intake")

    observed: dict[str, object] = {}
    ai_generator._openai_client = _make_openai_client(text="Role response", observed_kwargs=observed)

    result = await ai_generator.generate_legal_document_for_role("intake", "user")
    assert result.used_ai is True
    assert result.text == "Role response"
    assert result.model == "gpt-intake"
    assert observed.get("model") == "gpt-intake"


@pytest.mark.asyncio
async def test_generate_for_role_uses_compact_default_max_tokens_for_draft() -> None:
    object.__setattr__(settings, "ai_provider", "openai")
    object.__setattr__(settings, "openai_model_draft", "gpt-draft")

    observed: dict[str, object] = {}
    ai_generator._openai_client = _make_openai_client(text="ok", observed_kwargs=observed)

    result = await ai_generator.generate_legal_document_for_role("draft", "user")
    assert result.used_ai is True
    assert observed.get("model") == "gpt-draft"
    assert observed.get("max_tokens") == 1800


@pytest.mark.asyncio
async def test_generate_for_role_respects_explicit_max_tokens() -> None:
    object.__setattr__(settings, "ai_provider", "openai")
    object.__setattr__(settings, "openai_model_draft", "gpt-draft")

    observed: dict[str, object] = {}
    ai_generator._openai_client = _make_openai_client(text="ok", observed_kwargs=observed)

    result = await ai_generator.generate_legal_document_for_role(
        "draft",
        "user",
        options=ai_generator.AIGenerationOptions(max_tokens=3200),
    )
    assert result.used_ai is True
    assert observed.get("max_tokens") == 3200
