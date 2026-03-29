-- Legal AI Platform — bootstrap schema
-- Run once against a fresh PostgreSQL database.
-- The FastAPI app also runs these via SQLAlchemy metadata.create_all() on startup.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Users -------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    email         TEXT        NOT NULL UNIQUE,
    full_name     TEXT,
    password_hash TEXT,
    company       TEXT,
    entity_type   TEXT,
    tax_id        TEXT,
    address       TEXT,
    phone         TEXT,
    logo_url      TEXT,
    role          TEXT        NOT NULL DEFAULT 'user',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Subscriptions -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS subscriptions (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan         TEXT        NOT NULL DEFAULT 'FREE',
    docs_used    INT         NOT NULL DEFAULT 0,
    docs_limit   INT,                   -- NULL = unlimited
    period_start TIMESTAMPTZ DEFAULT NOW(),
    period_end   TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id)
);

-- Cases -------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cases (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title       TEXT        NOT NULL,
    description TEXT,
    case_number TEXT,
    status      TEXT        NOT NULL DEFAULT 'open',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cases_user_id ON cases(user_id);

-- Generated documents -----------------------------------------------------
CREATE TABLE IF NOT EXISTS generated_documents (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    case_id           UUID        REFERENCES cases(id) ON DELETE SET NULL,
    document_type     TEXT        NOT NULL,
    document_category TEXT        NOT NULL DEFAULT 'civil',
    title             TEXT,
    generated_text    TEXT        NOT NULL DEFAULT '',
    preview_text      TEXT,
    ai_model          TEXT,
    used_ai           BOOLEAN     NOT NULL DEFAULT true,
    has_docx_export   BOOLEAN     NOT NULL DEFAULT false,
    has_pdf_export    BOOLEAN     NOT NULL DEFAULT false,
    last_exported_at  TIMESTAMPTZ,
    e_court_ready     BOOLEAN     NOT NULL DEFAULT false,
    filing_blockers   JSONB       NOT NULL DEFAULT '[]',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_generated_documents_user_id    ON generated_documents(user_id);
CREATE INDEX IF NOT EXISTS idx_generated_documents_case_id    ON generated_documents(case_id);
CREATE INDEX IF NOT EXISTS idx_generated_documents_created_at ON generated_documents(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_generated_documents_type       ON generated_documents(document_type);
