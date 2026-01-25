-- ============================================
-- PostgreSQL Initialization Script
-- VibeCoding Customer Feedbacks Tracker
-- ============================================
-- Note: This script runs AFTER PostgreSQL creates the user and database
-- specified in POSTGRES_USER and POSTGRES_DB environment variables.
-- It only runs on FIRST initialization (when data directory is empty).

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search

-- ============================================
-- Posts table (main data)
-- ============================================
CREATE TABLE IF NOT EXISTS posts (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(50),
    author VARCHAR(255),
    content TEXT,
    url TEXT UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE,
    sentiment_score REAL,
    sentiment_label VARCHAR(20),
    language VARCHAR(20) DEFAULT 'unknown',
    country VARCHAR(100),
    relevance_score REAL DEFAULT 0.0,
    is_answered INTEGER DEFAULT 0,
    answered_at TIMESTAMP WITH TIME ZONE,
    answered_by VARCHAR(255),
    answer_detection_method VARCHAR(50),
    product VARCHAR(100),
    inserted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_posts_source ON posts(source);
CREATE INDEX IF NOT EXISTS idx_posts_sentiment ON posts(sentiment_label);
CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_language ON posts(language);
CREATE INDEX IF NOT EXISTS idx_posts_source_date ON posts(source, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_url ON posts(url);
CREATE INDEX IF NOT EXISTS idx_posts_product ON posts(product);
CREATE INDEX IF NOT EXISTS idx_posts_is_answered ON posts(is_answered);
CREATE INDEX IF NOT EXISTS idx_posts_content_trgm ON posts USING gin(content gin_trgm_ops);

-- ============================================
-- Saved queries / keywords table
-- ============================================
CREATE TABLE IF NOT EXISTS saved_queries (
    id BIGSERIAL PRIMARY KEY,
    keyword VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- Scraping logs table
-- ============================================
CREATE TABLE IF NOT EXISTS scraping_logs (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    source VARCHAR(50),
    level VARCHAR(20),
    message TEXT,
    details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON scraping_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_logs_source ON scraping_logs(source);
CREATE INDEX IF NOT EXISTS idx_logs_level ON scraping_logs(level);

-- ============================================
-- Base keywords table
-- ============================================
CREATE TABLE IF NOT EXISTS base_keywords (
    id BIGSERIAL PRIMARY KEY,
    category VARCHAR(100) NOT NULL,
    keyword VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(category, keyword)
);

-- ============================================
-- Jobs queue table (for Redis fallback/persistence)
-- ============================================
CREATE TABLE IF NOT EXISTS job_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_type VARCHAR(50) NOT NULL,
    payload JSONB NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    priority INTEGER DEFAULT 0,
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    scheduled_for TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON job_queue(status);
CREATE INDEX IF NOT EXISTS idx_jobs_scheduled ON job_queue(scheduled_for) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_jobs_type ON job_queue(job_type);

-- ============================================
-- Job results/history table
-- ============================================
CREATE TABLE IF NOT EXISTS job_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES job_queue(id) ON DELETE SET NULL,
    job_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    result JSONB,
    duration_seconds REAL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_job_results_created ON job_results(created_at DESC);

-- ============================================
-- Users table (for authentication)
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE
);

-- ============================================
-- API tokens table
-- ============================================
CREATE TABLE IF NOT EXISTS api_tokens (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100),
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_tokens_user ON api_tokens(user_id);

-- ============================================
-- Config table (for app settings)
-- ============================================
CREATE TABLE IF NOT EXISTS app_config (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Insert default config
INSERT INTO app_config (key, value) VALUES 
    ('scraping_enabled', 'true'::jsonb),
    ('auto_scrape_interval_hours', '3'::jsonb),
    ('max_posts_per_query', '50'::jsonb)
ON CONFLICT (key) DO NOTHING;

-- ============================================
-- Function to clean old logs (keep 30 days)
-- ============================================
CREATE OR REPLACE FUNCTION clean_old_logs() RETURNS void AS $$
BEGIN
    DELETE FROM scraping_logs 
    WHERE created_at < NOW() - INTERVAL '30 days';
    
    DELETE FROM job_results 
    WHERE created_at < NOW() - INTERVAL '7 days';
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- Grant permissions
-- ============================================
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ocft_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ocft_user;
