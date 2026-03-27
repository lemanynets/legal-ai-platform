-- Legacy SQL snapshot.
-- Prefer schema management via Alembic migrations in backend/migrations.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    company VARCHAR(255),
    role VARCHAR(50) DEFAULT 'user',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    plan VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    analyses_used INT DEFAULT 0,
    analyses_limit INT DEFAULT 3,
    docs_used INT DEFAULT 0,
    docs_limit INT DEFAULT 1,
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS contract_analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    file_name VARCHAR(500),
    file_url TEXT,
    file_size INT,
    contract_type VARCHAR(255),
    risk_level VARCHAR(50),
    critical_risks JSONB,
    medium_risks JSONB,
    ok_points JSONB,
    recommendations JSONB,
    ai_model VARCHAR(100),
    tokens_used INT,
    processing_time_ms INT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS generated_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    document_type VARCHAR(100),
    document_category VARCHAR(50),
    form_data JSONB,
    generated_text TEXT,
    docx_url TEXT,
    pdf_url TEXT,
    court_fee_amount DECIMAL(10, 2),
    ai_model VARCHAR(100),
    tokens_used INT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    liqpay_order_id VARCHAR(255) UNIQUE,
    amount DECIMAL(10, 2),
    currency VARCHAR(10) DEFAULT 'UAH',
    plan VARCHAR(50),
    status VARCHAR(50),
    liqpay_response JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS deadlines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    title VARCHAR(500),
    document_id UUID REFERENCES generated_documents(id),
    deadline_type VARCHAR(100),
    start_date DATE,
    end_date DATE,
    reminder_sent BOOLEAN DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100),
    entity_type VARCHAR(50),
    entity_id UUID,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS intake_analysis_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    jurisdiction VARCHAR(10) NOT NULL DEFAULT 'UA',
    mode VARCHAR(20) NOT NULL DEFAULT 'standard',
    source_file_name VARCHAR(500),
    result JSONB NOT NULL,
    ai_model VARCHAR(100),
    tokens_used INT,
    processing_time_ms INT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '30 days'),
    CONSTRAINT uq_intake_cache_key UNIQUE (user_id, content_hash, jurisdiction, mode)
);

CREATE INDEX IF NOT EXISTS idx_intake_cache_lookup
    ON intake_analysis_cache (user_id, content_hash, jurisdiction, mode)
    WHERE expires_at > NOW();

CREATE TABLE IF NOT EXISTS gdpr_checks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    intake_id UUID,
    compliant BOOLEAN NOT NULL DEFAULT FALSE,
    issues JSONB DEFAULT '[]'::jsonb,
    personal_data_found JSONB DEFAULT '[]'::jsonb,
    recommendations JSONB DEFAULT '[]'::jsonb,
    report TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
