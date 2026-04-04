from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw.strip())
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw.strip())
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Legal AI Platform API")
    app_version: str = os.getenv("APP_VERSION", "0.1.0")
    app_env: str = os.getenv("APP_ENV", os.getenv("ENV", "development")).strip().lower() or "development"
    database_url: str = os.getenv("DATABASE_URL", "").strip() or os.getenv(
        "SUPABASE_DATABASE_URL",
        "postgresql+psycopg://legal_ai:legal_ai@localhost:5432/legal_ai",
    )
    ai_provider: str = os.getenv("AI_PROVIDER", "openai").strip().lower() or "openai"
    ai_fallback_enabled: bool = _env_bool("AI_FALLBACK_ENABLED", True)
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    # Optional role-based model overrides (used by 3-agent pipeline)
    openai_model_intake: str = os.getenv("OPENAI_MODEL_INTAKE", "").strip() or openai_model
    openai_model_research: str = os.getenv("OPENAI_MODEL_RESEARCH", "").strip() or openai_model
    openai_model_draft: str = os.getenv("OPENAI_MODEL_DRAFT", "").strip() or openai_model
    openai_model_strategy: str = os.getenv("OPENAI_MODEL_STRATEGY", "").strip() or openai_model

    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
    anthropic_model_intake: str = os.getenv("ANTHROPIC_MODEL_INTAKE", "").strip() or anthropic_model
    anthropic_model_research: str = os.getenv("ANTHROPIC_MODEL_RESEARCH", "").strip() or anthropic_model
    anthropic_model_draft: str = os.getenv("ANTHROPIC_MODEL_DRAFT", "").strip() or anthropic_model
    anthropic_model_strategy: str = os.getenv("ANTHROPIC_MODEL_STRATEGY", "").strip() or anthropic_model

    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    gemini_model_intake: str = os.getenv("GEMINI_MODEL_INTAKE", "").strip() or gemini_model
    gemini_model_research: str = os.getenv("GEMINI_MODEL_RESEARCH", "").strip() or gemini_model
    gemini_model_draft: str = os.getenv("GEMINI_MODEL_DRAFT", "").strip() or gemini_model
    gemini_model_strategy: str = os.getenv("GEMINI_MODEL_STRATEGY", "").strip() or gemini_model

    ai_intake_openai_model: str = os.getenv("AI_INTAKE_OPENAI_MODEL", "gpt-4o-mini").strip()
    ai_intake_anthropic_model: str = os.getenv("AI_INTAKE_ANTHROPIC_MODEL", "claude-3-5-haiku-latest").strip()
    ai_intake_gemini_model: str = os.getenv("AI_INTAKE_GEMINI_MODEL", "gemini-1.5-flash").strip()
    ai_intake_temperature: float = min(max(_env_float("AI_INTAKE_TEMPERATURE", 0.1), 0.0), 1.0)
    ai_intake_max_tokens: int = max(128, _env_int("AI_INTAKE_MAX_TOKENS", 500))
    ai_precedent_openai_model: str = os.getenv("AI_PRECEDENT_OPENAI_MODEL", "gpt-4.1").strip()
    ai_precedent_anthropic_model: str = os.getenv(
        "AI_PRECEDENT_ANTHROPIC_MODEL",
        "claude-3-5-sonnet-20241022",
    ).strip()
    ai_precedent_gemini_model: str = os.getenv("AI_PRECEDENT_GEMINI_MODEL", "gemini-1.5-pro").strip()
    ai_precedent_temperature: float = min(max(_env_float("AI_PRECEDENT_TEMPERATURE", 0.2), 0.0), 1.0)
    ai_precedent_max_tokens: int = max(256, _env_int("AI_PRECEDENT_MAX_TOKENS", 1500))
    ai_deep_openai_model: str = os.getenv("AI_DEEP_OPENAI_MODEL", "gpt-4-turbo").strip()
    ai_deep_anthropic_model: str = os.getenv("AI_DEEP_ANTHROPIC_MODEL", "claude-3-opus-20240229").strip()
    ai_deep_gemini_model: str = os.getenv("AI_DEEP_GEMINI_MODEL", "gemini-1.5-pro").strip()
    ai_deep_temperature: float = min(max(_env_float("AI_DEEP_TEMPERATURE", 0.3), 0.0), 1.0)
    ai_deep_max_tokens: int = max(512, _env_int("AI_DEEP_MAX_TOKENS", 4000))
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_anon_key: str = os.getenv("SUPABASE_ANON_KEY", "")
    supabase_storage_bucket: str = os.getenv("SUPABASE_STORAGE_BUCKET", "legal-documents")
    # SECURITY: set ALLOW_DEV_AUTH=false in production!
    allow_dev_auth: bool = _env_bool("ALLOW_DEV_AUTH", False)
    allowed_dev_demo_users: str = os.getenv("ALLOWED_DEV_DEMO_USERS", "demo-user,test-user").strip()
    # JWT: REQUIRED in production! Generate with: python -c "import secrets; print(secrets.token_urlsafe(64))"
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "").strip()
    jwt_issuer: str = os.getenv("JWT_ISSUER", "legal-ai-platform").strip() or "legal-ai-platform"
    jwt_audience: str = os.getenv("JWT_AUDIENCE", "legal-ai-api").strip() or "legal-ai-api"
    allow_legacy_jwt: bool = _env_bool("ALLOW_LEGACY_JWT", app_env in {"local", "dev", "development", "test"})
    document_encryption_key: str = os.getenv("DOCUMENT_ENCRYPTION_KEY", "").strip()
    redis_url: str = os.getenv("REDIS_URL", "").strip()
    # CORS: restrict in production, e.g. ALLOWED_ORIGINS=https://your-domain.com
    allowed_origins: str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001").strip()
    rate_limit_default: str = os.getenv("RATE_LIMIT_DEFAULT", "100/minute")
    # Remote logos are allowed only from explicitly approved HTTPS hosts.
    document_logo_allowed_hosts: str = os.getenv("DOCUMENT_LOGO_ALLOWED_HOSTS", "").strip()
    liqpay_public_key: str = os.getenv("LIQPAY_PUBLIC_KEY", "")
    liqpay_private_key: str = os.getenv("LIQPAY_PRIVATE_KEY", "")
    liqpay_server_url: str = os.getenv("LIQPAY_SERVER_URL", "")
    liqpay_result_url: str = os.getenv("LIQPAY_RESULT_URL", "")
    liqpay_checkout_url: str = os.getenv("LIQPAY_CHECKOUT_URL", "https://www.liqpay.ua/api/3/checkout")
    subscription_period_days: int = max(1, _env_int("SUBSCRIPTION_PERIOD_DAYS", 30))
    opendatabot_api_key: str = os.getenv("OPENDATABOT_API_KEY", "")
    opendatabot_api_url: str = os.getenv("OPENDATABOT_API_URL", "https://api.opendatabot.ua/v2")
    opendatabot_request_limit: int = max(1, _env_int("OPENDATABOT_REQUEST_LIMIT", 20))
    opendatabot_expires_at: str = os.getenv("OPENDATABOT_EXPIRES_AT", "2026-03-30").strip()
    case_law_auto_sync_enabled: bool = _env_bool("CASE_LAW_AUTO_SYNC_ENABLED", False)
    case_law_auto_sync_interval_minutes: int = max(1, _env_int("CASE_LAW_AUTO_SYNC_INTERVAL_MINUTES", 360))
    case_law_auto_sync_limit: int = max(1, min(_env_int("CASE_LAW_AUTO_SYNC_LIMIT", 100), 200))
    case_law_auto_sync_query: str = os.getenv("CASE_LAW_AUTO_SYNC_QUERY", "").strip()
    case_law_auto_sync_sources: str = os.getenv("CASE_LAW_AUTO_SYNC_SOURCES", "opendatabot,json_feed").strip()
    case_law_allow_seed_fallback: bool = _env_bool("CASE_LAW_ALLOW_SEED_FALLBACK", True)
    case_law_auto_sync_run_on_start: bool = _env_bool("CASE_LAW_AUTO_SYNC_RUN_ON_START", True)
    case_law_json_feed_url: str = os.getenv("CASE_LAW_JSON_FEED_URL", "").strip()
    case_law_generation_max_age_days: int = max(30, _env_int("CASE_LAW_GENERATION_MAX_AGE_DAYS", 3650))
    case_law_generation_supreme_only: bool = _env_bool("CASE_LAW_GENERATION_SUPREME_ONLY", True)
    case_law_generation_min_relevance_score: float = min(
        max(_env_float("CASE_LAW_GENERATION_MIN_RELEVANCE_SCORE", 0.25), 0.0),
        1.0,
    )
    case_law_digest_auto_enabled: bool = _env_bool("CASE_LAW_DIGEST_AUTO_ENABLED", False)
    case_law_digest_auto_interval_hours: int = max(1, _env_int("CASE_LAW_DIGEST_AUTO_INTERVAL_HOURS", 168))
    case_law_digest_auto_days: int = max(1, min(_env_int("CASE_LAW_DIGEST_AUTO_DAYS", 7), 3650))
    case_law_digest_auto_limit: int = max(1, min(_env_int("CASE_LAW_DIGEST_AUTO_LIMIT", 20), 100))
    case_law_digest_auto_only_supreme: bool = _env_bool("CASE_LAW_DIGEST_AUTO_ONLY_SUPREME", True)
    case_law_digest_auto_run_on_start: bool = _env_bool("CASE_LAW_DIGEST_AUTO_RUN_ON_START", False)
    auto_process_processual_only_default: bool = _env_bool("AUTO_PROCESS_PROCESSUAL_ONLY_DEFAULT", True)
    registry_monitor_auto_enabled: bool = _env_bool("REGISTRY_MONITOR_AUTO_ENABLED", False)
    registry_monitor_auto_interval_minutes: int = max(1, _env_int("REGISTRY_MONITOR_AUTO_INTERVAL_MINUTES", 60))
    registry_monitor_auto_check_limit: int = max(1, min(_env_int("REGISTRY_MONITOR_AUTO_CHECK_LIMIT", 50), 500))
    registry_monitor_auto_run_on_start: bool = _env_bool("REGISTRY_MONITOR_AUTO_RUN_ON_START", False)
    document_storage_root: str = os.getenv("DOCUMENT_STORAGE_ROOT", "data/generated_exports").strip()
    full_lawyer_urgent_window_days: int = max(1, min(_env_int("FULL_LAWYER_URGENT_WINDOW_DAYS", 5), 30))
    full_lawyer_clarification_deadline_days: int = max(1, min(_env_int("FULL_LAWYER_CLARIFICATION_DEADLINE_DAYS", 2), 30))
    full_lawyer_filing_target_days: int = max(1, min(_env_int("FULL_LAWYER_FILING_TARGET_DAYS", 5), 60))
    full_lawyer_response_window_days: int = max(1, min(_env_int("FULL_LAWYER_RESPONSE_WINDOW_DAYS", 15), 90))
    full_lawyer_timeline_target_days: int = max(1, min(_env_int("FULL_LAWYER_TIMELINE_TARGET_DAYS", 7), 60))
    appeal_deadline_days: int = max(1, min(_env_int("APPEAL_DEADLINE_DAYS", 30), 120))
    cassation_deadline_days: int = max(1, min(_env_int("CASSATION_DEADLINE_DAYS", 30), 120))
    strict_filing_mode: bool = _env_bool("STRICT_FILING_MODE", True)
    # E-Court (court.gov.ua) Integration
    # Register at https://court.gov.ua to get client credentials.
    # Leave blank to run in stub mode (no real API calls).
    court_gov_ua_test_mode: bool = _env_bool("COURT_GOV_UA_TEST_MODE", True)
    court_gov_ua_api_base: str = os.getenv(
        "COURT_GOV_UA_API_BASE",
        "https://test-api-corp.court.gov.ua",
    ).rstrip("/")
    court_gov_ua_client_id: str = os.getenv("COURT_GOV_UA_CLIENT_ID", "").strip()
    court_gov_ua_client_secret: str = os.getenv("COURT_GOV_UA_CLIENT_SECRET", "").strip()
    
    # ECP (КЕП) Signature Settings
    ecp_key_path: str = os.getenv("ECP_KEY_PATH", "Key-6.pfx").strip()
    ecp_key_password: str = os.getenv("ECP_KEY_PASSWORD", "").strip()


settings = Settings()
