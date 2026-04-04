# Legal AI Platform

Starter monorepo for the new product described in your technical specification.

## Sprint Plan

### Sprint 1 (Core MVP, 2 weeks)
- Monorepo setup (`frontend`, `backend`, `database`, CI, docker compose).
- FastAPI skeleton with key modules:
  - documents catalog and generation preview
  - court fee/penalty/deadline calculators
  - billing plans endpoints
- PostgreSQL schema baseline.
- Next.js dashboard shell and core pages.

### Sprint 2 (Production-ready MVP, 2 weeks)
- OpenAI/Claude integration with fallback.
- DOCX/PDF generation pipeline and storage integration.
- Supabase Auth + subscription limits + audit logging.
- LiqPay webhook and billing workflows.
- Monitoring, rate limit, and test hardening.

## Monorepo structure

```text
legal-ai-platform/
  frontend/
  backend/
  database/
  .github/workflows/
  docker-compose.yml
```

## Local quick start

1. Backend:
   - `cd legal-ai-platform/backend`
   - `python -m venv .venv`
   - `.\.venv\Scripts\activate`
   - `pip install -r requirements.txt`
   - `alembic upgrade head`
   - `uvicorn app.main:app --reload --port 8000`
2. Frontend:
   - `cd legal-ai-platform/frontend`
   - `npm install`
   - `npm run dev`
   - `npm test`
3. Docker (optional):
   - `cd legal-ai-platform`
   - `docker compose up --build`
   - backend container runs `alembic upgrade head` automatically before API start.

## Environment

- Copy `legal-ai-platform/.env.example` to `.env`.
- Copy `legal-ai-platform/frontend/.env.example` to `frontend/.env.local`.
- Important variables:
  - `AI_PROVIDER` (`openai` | `anthropic` | `gemini` | `auto`)
  - `OPENAI_API_KEY`, `OPENAI_MODEL`

## Security

- Never commit secrets (.env files, API keys) to git.
- Use `pre-commit install` to enable security hooks (gitleaks for secret scanning).
- Rate limiting is enabled by default (100 requests/minute).
- In production, set `ALLOW_DEV_AUTH=false`.
  - `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`
  - `GEMINI_API_KEY`, `GEMINI_MODEL`
  - `SUPABASE_URL`, `SUPABASE_ANON_KEY`
  - `ALLOW_DEV_AUTH=true` for local testing without real JWT.
  - `SUBSCRIPTION_PERIOD_DAYS` for billing-cycle quota reset window (default `30`)
  - `CASE_LAW_AUTO_SYNC_ENABLED`, `CASE_LAW_AUTO_SYNC_INTERVAL_MINUTES`, `CASE_LAW_AUTO_SYNC_LIMIT`
  - `CASE_LAW_AUTO_SYNC_SOURCES`, `CASE_LAW_ALLOW_SEED_FALLBACK`, `CASE_LAW_JSON_FEED_URL`
  - `REGISTRY_MONITOR_AUTO_ENABLED`, `REGISTRY_MONITOR_AUTO_INTERVAL_MINUTES`, `REGISTRY_MONITOR_AUTO_CHECK_LIMIT`
  - `CASE_LAW_GENERATION_MAX_AGE_DAYS` to prefer recent practice in AI generation
  - `CASE_LAW_GENERATION_SUPREME_ONLY` to prioritize Supreme Court practice in generation prompts
  - `AUTO_PROCESS_PROCESSUAL_ONLY_DEFAULT=true` to keep auto-generated packages focused on procedural court filings
  - `FULL_LAWYER_URGENT_WINDOW_DAYS` threshold (days) for `urgent` deadline status in Full Lawyer
  - `FULL_LAWYER_CLARIFICATION_DEADLINE_DAYS`, `FULL_LAWYER_FILING_TARGET_DAYS`, `FULL_LAWYER_RESPONSE_WINDOW_DAYS`
  - `FULL_LAWYER_TIMELINE_TARGET_DAYS` for procedural timeline target filing marker
  - `APPEAL_DEADLINE_DAYS`, `CASSATION_DEADLINE_DAYS` for configurable appellate checkpoints
  - `STRICT_FILING_MODE=true` to enforce PASS-only final submission gate before e-court submission
  - `DOCUMENT_STORAGE_ROOT` for persistent DOCX/PDF export cache
  - For Supabase Postgres set `DATABASE_URL=postgresql+psycopg://...:6543/postgres?sslmode=require`.

## Implemented now

- Frontend pages are connected to backend APIs:
  - `/dashboard/analyze` -> contract analysis process/history
  - `/dashboard/generate` -> documents types/schema/generate
  - `/dashboard/billing` -> plans/subscribe/subscription + `/auth/me` + LiqPay checkout payload
  - `/dashboard/documents` -> history + edit/clone/delete + DOCX/PDF export + bulk delete + CSV/ZIP history export + E-Court submission panel (PRO+)
  - `/dashboard/audit` -> user audit history with filters/pagination
  - `/dashboard/case-law` -> server-side search/sort/pagination + import/sync + use-in-prompt action
  - `/dashboard/monitoring` -> registry watchlist + check-now + monitoring events (PRO+)
  - `/dashboard/calculators` -> full claim calculator (fee + penalty + deadlines + limitation) with saved history
  - `/dashboard/auto-process` -> upload any case file and auto-generate draft process documents
  - `/dashboard/full-lawyer` -> upload file and receive full strategy/evidence/risks + generated document package
- Backend generation endpoint supports OpenAI + Claude/Anthropic + Gemini with configurable fallback chain.
- Full claim calculator module (`M9`) is available via `/api/calculate/full` with per-user history persistence.
- Auto-process module accepts uploaded files (`txt/pdf/docx/doc/rtf`) and generates procedural conclusions + document drafts.
- `/api/documents/generate` supports optional prompt enrichment:
  - `extra_prompt_context`
  - `saved_digest_id` (loads user-saved digest snapshot directly into prompt context)
  - digest flags (`include_digest`, `digest_days`, `digest_limit`, `digest_only_supreme`, `digest_court_type`, `digest_source`)
  - auto-injected `Case law references for motivation section` for top claim types
- Contract analyses are persisted in PostgreSQL via `/api/analyze/*` with tariff limits.
- Supabase Auth token validation is wired through `/auth/me` and protected endpoints.
- Per-user subscriptions and usage limits are persisted in PostgreSQL (SQLAlchemy).
- Generated documents are saved to PostgreSQL and returned by `/api/documents/history`.
- Generated documents can be exported as DOCX/PDF via `/api/documents/{id}/export?format=docx|pdf`.
- Exported DOCX/PDF files are cached in local storage (`DOCUMENT_STORAGE_ROOT`) and reflected in history flags.
- Generated documents can be edited via `/api/documents/{id}` (`PATCH`), which invalidates cached exports.
- Generated documents can be auto-repaired to processual fallback structure via `/api/documents/{id}/processual-repair` (`POST`).
- Generated documents can be checked for processual blockers via `/api/documents/{id}/processual-check` (`GET`).
- Selected documents can be repaired in bulk via `/api/documents/bulk-processual-repair` (`POST`).
- Generated documents can be deleted via `/api/documents/{id}` (`DELETE`) with export file cleanup.
- Generated documents can be bulk-deleted via `/api/documents/bulk-delete` (`POST`).
- Generated documents detail is available via `/api/documents/{id}` (`GET`).
- Generated documents can be cloned via `/api/documents/{id}/clone` (`POST`) with usage counter update.
- Document versions are available via `/api/documents/{id}/versions` (`GET`).
- Single version content is available via `/api/documents/{id}/versions/{version_id}` (`GET`).
- Version diff is available via `/api/documents/{id}/versions/{version_id}/diff` (`GET`).
- Document text can be restored from a saved version via `/api/documents/{id}/versions/{version_id}/restore` (`POST`).
- `/api/documents/history` supports server pagination/filter/sort (`page`, `page_size`, `query`, `doc_type`, `has_docx_export`, `has_pdf_export`, `sort_by`, `sort_dir`).
- `/api/documents/history/export` supports filtered export to `csv`/`zip`.
- Deadline CRUD is persisted in PostgreSQL via `/api/deadlines`.
- Calculation history is persisted in PostgreSQL via `/api/calculate/history` and `/api/calculate/{id}`.
- Audit log is written for auth/analyze/generate/billing/deadline actions.
- Audit history API is available at `/api/audit/history`.
- LiqPay integration:
  - subscribe creates pending payment with `liqpay_order_id`
  - paid plan is activated only after successful LiqPay webhook confirmation
  - monthly (configurable) billing period rollover resets usage counters automatically
  - webhook handler is idempotent (`duplicate=true` on repeated same event) and does not re-activate/reset usage on retries
  - webhook replay protection uses persisted event IDs (`payment_webhook_events`) before subscription activation logic
  - checkout payload (`liqpay_data` + `liqpay_signature`) is returned by `/api/billing/subscribe`
  - webhook endpoint `/api/billing/webhook/liqpay` validates signature and updates payment/subscription status
- Case law module:
  - case-law cache tables (`case_law_cache`, `document_case_law_refs`) added
  - `/api/documents/generate` enriches prompts with relevant case-law and stores references
  - `/api/case-law/search` supports query/court_type/tags + server pagination/sorting (`page`, `page_size`, `sort_by`, `sort_dir`)
  - `/api/case-law/search` also supports `source`, `date_from`, `date_to`, `fresh_days`, `only_supreme` filters
  - `/api/case-law/digest` returns weekly/latest digest items ready for prompt enrichment
  - `/api/case-law/digest/generate` can optionally save digest snapshot for user history (`save=true`)
  - `/api/case-law/digest/history` and `/api/case-law/digest/history/{id}` expose saved digest history/details
  - `/api/case-law/import` upserts records into cache
  - `/api/case-law/sync` syncs from Opendatabot API (if configured) with seed fallback
  - `/api/case-law/sync/status` returns last sync metadata and source coverage
  - entitlement gating:
    - saved digests (`save=true`, history/detail) require `PRO` or higher
    - import/sync/sync-status (monitoring flow) require `PRO_PLUS` or higher
  - `/dashboard/case-law` shows current plan/status and disables restricted actions with clear PRO/PRO+ hints
  - optional background auto-sync loop on app startup (`CASE_LAW_AUTO_SYNC_ENABLED=true`)
  - `/dashboard/generate` can load digest into additional context and pass digest options to generation
  - `/dashboard/case-law` includes saved digest history and open/save actions
- E-Court module (PRO+):
  - `/api/e-court/submit` submits generated document to e-court queue (stub provider flow)
  - `/api/e-court/history` returns per-user submission history with pagination/filter by status
  - `/api/e-court/{id}/status` returns current submission status/tracking data
- Registry monitoring module (PRO+):
  - `/api/monitoring/watch-items` creates/returns watchlist items for selected registry identifiers
  - `/api/monitoring/watch-items/{id}/check` runs manual status check and creates monitoring event
  - `/api/monitoring/check-due` runs batch checks for due watch items
  - `/api/monitoring/status` returns dashboard summary (due/warnings/changes)
  - `/api/monitoring/watch-items/{id}` (`DELETE`) removes watch item with all events
  - `/api/monitoring/events` returns monitoring event stream with filters/pagination
  - optional background auto-check loop on app startup (`REGISTRY_MONITOR_AUTO_ENABLED=true`)
- M9 calculators module:
  - `/api/calculate/full` computes court fee + penalty + process deadline + limitation deadline and can save run history
  - `/api/calculate/history` returns saved calculation runs for current user
  - `/api/calculate/{id}` returns saved calculation details
- Auto-process module:
  - `/api/auto/process` uploads a file, extracts text, builds procedural conclusions, and auto-generates recommended drafts
  - `/api/auto/full-lawyer` uploads a file and returns structured legal strategy + evidence/risk checklist + generated drafts
  - `processual_only` mode is enabled by default for auto/full-lawyer to prioritize court-process documents only
  - `full-lawyer` response now includes:
    - clarifying questions list (facts to confirm before filing)
    - clarification gate (`status=needs_clarification`) that blocks final generation until unanswered questions are provided in `clarifications_json`
    - rule-based pre-checks (claim amount, parties, limitation, procedure route, appeal timing)
    - RAG context refs (case-law snippets + primary law references)
    - confidence score + next actions checklist
    - estimated court fee / penalty / total-with-fee snapshot
    - optional one-click filing package generation (`generate_package=true`) with cover + evidence inventory docs
    - strict processual package gate that blocks package generation when generated drafts still have unresolved processual blockers
- Alembic migrations:
  - `backend/migrations/versions/20260218_0001_core_tables.py`
  - `backend/migrations/versions/20260218_0002_ops_tables.py`
  - `backend/migrations/versions/20260218_0003_case_law_cache.py`
  - `backend/migrations/versions/20260218_0004_document_export_storage.py`
  - `backend/migrations/versions/20260218_0005_document_versions.py`
  - `backend/migrations/versions/20260221_0006_case_law_digests.py`
  - `backend/migrations/versions/20260222_0007_payment_webhook_events.py`
  - `backend/migrations/versions/20260222_0008_court_submissions.py`
  - `backend/migrations/versions/20260222_0009_registry_monitoring.py`
  - `backend/migrations/versions/20260222_0010_calculation_runs.py`
- Agentic pipeline for automated legal workflows.
- Cases module for managing legal cases.
- Forum for user discussions and community support.
- Knowledge base for centralized legal resources and documents.
- Judge simulator for predicting case outcomes based on historical data.

## Current status

- Full platform v2 implemented with agentic pipeline, cases, forum, knowledge base, judge simulator.
- Sprint 1 scaffold is now interactive and API-connected.
- Remaining production work: real LiqPay production keys/callback URLs, file storage (R2), production-grade DOCX/PDF templates.

## Implementation Plan from Audit

### Refactoring: Split main.py into modules
- Create app/lifespan.py for startup/shutdown logic. ✅
- Create app/middleware.py for custom middleware. ✅
- Create app/deps.py for dependencies. ✅
- Create services/rate_limiting.py for rate limiting functions. ✅
- Create app/app_config.py for app creation and middleware setup. ✅
- main.py reduced from 3691 to 42 lines. ✅

### High Priority
- Add support for more file formats (images with OCR, audio transcripts). ✅
- Integrate GDPR redaction with NLP for PII detection and auto-redaction. ✅

### 2. Backend Tests (High Priority - Regression Protection)
- Health endpoint test: ✅ (existing)
- Auth login/me tests: ✅ (added basic)
- Next: Documents generate, Analyze intake with DB fixtures.

### Medium Priority
- Scale real-time AI feedback to intake/strategy/full-lawyer endpoints. ✅
- Add ML auto-tagging for analyses with managed taxonomy.
- Implement collaborative features (comments/assignments/approval trail) for analyses.
- Add customizable templates with drag-and-drop editor.
- Integrate multi-language generation with auto-translation.
- Connect version control UI (diff view, rollback buttons) in documents page.
- Add real-time collaboration for editing (presence/locking with WebSockets).
- Optimize export to R2 with signed URLs.
- Implement smart defaults based on user history and preferences.

## Potential Improvements

### Document Analysis Improvements
- Add support for more file formats (e.g., images with OCR, audio transcripts).
- Implement real-time AI feedback during analysis for faster user experience.
- Enhance GDPR checks with automatic redacting of sensitive data.
- Integrate machine learning for auto-tagging and categorization of analyses.
- Add collaborative features for multi-user review of analyses.
- Optimize batch processing with parallel AI calls for speed.
- Implement caching for repeated analyses of identical files.

### Document Generation Improvements
- Add customizable templates with drag-and-drop editor.
- Implement AI-powered auto-correction and grammar checking.
- Support multi-language generation with auto-translation.
- Integrate version control with diff view and rollback.
- Add real-time collaboration for editing generated documents.
- Optimize export to R2 with signed URLs for security.
- Implement smart defaults based on user history and preferences.

## Sprint 2 — Стабільність

### 4. Розбити main.py на роутер-модулі [HIGH] ✅
- Створено routers/auth.py, documents.py, analyze.py, strategy.py, auto_process.py, case_law.py, monitoring.py, registries.py.
- main.py скорочено до 42 рядків з include_router.

### 5. Кеш аналізу за MD5 файлу [MEDIUM] ✅
- Додано intake_cache таблицю з міграцією.
- MD5 обчислення для intake запитів, перевірка/збереження кешу в analyze_intake.

### 6. Preflight gate перед пакетною генерацією [MEDIUM] ✅
- Додано preflight check в generate для bundle_doc_types.
- Блокування генерації якщо є unresolved questions або review items.

### 7. Unified AnalysisResult DTO [MEDIUM] ✅
- Створено UnifiedAnalysisResult schema для єдиного інтерфейсу аналізів.

## Sprint 4 — Інфраструктура

### 8. Backend pytest тести [MEDIUM] ✅
- Додано базові тести для generate, documents history.

### 9. Розбити api.ts на модулі [LOW] ✅
- Створено структуру lib/api/analyze.ts, lib/api/documents.ts тощо.

### 10. Analytics events [LOW] ✅
- Таблиця analytics_events з міграцією, трекінг completion, export, error events.
