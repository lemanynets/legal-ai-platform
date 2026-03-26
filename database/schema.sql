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
