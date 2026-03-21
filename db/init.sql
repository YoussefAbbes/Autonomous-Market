-- ============================================================================
-- Autonomous Market Intelligence - Phase 1 schema bootstrap
-- ============================================================================
-- This script creates the two foundation tables requested for time-series data:
--   1) asset_prices
--   2) market_news
--
-- Notes:
-- - We keep the exact "timestamp" column name requested by the project brief.
-- - We add constraints and indexes for performance and data quality.
-- - BRIN indexes help with append-heavy time-series workloads.
-- ============================================================================

CREATE TABLE IF NOT EXISTS asset_prices (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    price NUMERIC(20, 8) NOT NULL CHECK (price >= 0),
    "timestamp" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    volume NUMERIC(30, 8),
    source TEXT NOT NULL DEFAULT 'coingecko',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(symbol, "timestamp", source)
);

CREATE INDEX IF NOT EXISTS idx_asset_prices_symbol_timestamp_desc
    ON asset_prices (symbol, "timestamp" DESC);

CREATE INDEX IF NOT EXISTS idx_asset_prices_timestamp_brin
    ON asset_prices USING BRIN ("timestamp");

CREATE TABLE IF NOT EXISTS market_news (
    id BIGSERIAL PRIMARY KEY,
    headline TEXT NOT NULL,
    source TEXT NOT NULL,
    "timestamp" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ai_sentiment_score DOUBLE PRECISION,
    url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_market_news_source_timestamp_desc
    ON market_news (source, "timestamp" DESC);

CREATE INDEX IF NOT EXISTS idx_market_news_timestamp_brin
    ON market_news USING BRIN ("timestamp");

-- Convenience view for fast "latest per symbol" queries used by dashboards/MCP.
CREATE OR REPLACE VIEW latest_asset_prices AS
SELECT DISTINCT ON (symbol)
    symbol,
    price,
    volume,
    "timestamp",
    source
FROM asset_prices
ORDER BY symbol, "timestamp" DESC;
