-- ============================================================================
-- Migration 002: Multi-currency support and additional market data
-- ============================================================================

-- Add new columns to asset_prices for multi-currency and market data
ALTER TABLE asset_prices
ADD COLUMN IF NOT EXISTS currency TEXT NOT NULL DEFAULT 'usd',
ADD COLUMN IF NOT EXISTS market_cap NUMERIC(30, 2),
ADD COLUMN IF NOT EXISTS change_24h NUMERIC(10, 4),
ADD COLUMN IF NOT EXISTS price_eur NUMERIC(20, 8),
ADD COLUMN IF NOT EXISTS price_gbp NUMERIC(20, 8),
ADD COLUMN IF NOT EXISTS price_jpy NUMERIC(20, 2);

-- Drop the old unique constraint and create new one with currency
ALTER TABLE asset_prices DROP CONSTRAINT IF EXISTS asset_prices_symbol_timestamp_source_key;
ALTER TABLE asset_prices ADD CONSTRAINT asset_prices_symbol_timestamp_currency_source_key
    UNIQUE(symbol, "timestamp", currency, source);

-- Create exchange rates table for currency conversion
CREATE TABLE IF NOT EXISTS exchange_rates (
    id SERIAL PRIMARY KEY,
    base_currency TEXT NOT NULL DEFAULT 'usd',
    target_currency TEXT NOT NULL,
    rate NUMERIC(20, 8) NOT NULL,
    "timestamp" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source TEXT NOT NULL DEFAULT 'coingecko',
    UNIQUE(base_currency, target_currency, "timestamp")
);

CREATE INDEX IF NOT EXISTS idx_exchange_rates_currencies
    ON exchange_rates (base_currency, target_currency, "timestamp" DESC);

-- Create alerts table for storing triggered alerts
CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    type TEXT NOT NULL,
    symbol TEXT,
    message TEXT NOT NULL,
    severity TEXT DEFAULT 'info',
    metadata JSONB,
    notified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_notified ON alerts(notified) WHERE notified = FALSE;

-- Update the latest_asset_prices view
CREATE OR REPLACE VIEW latest_asset_prices AS
SELECT DISTINCT ON (symbol)
    symbol,
    price,
    volume,
    market_cap,
    change_24h,
    price_eur,
    price_gbp,
    price_jpy,
    "timestamp",
    source
FROM asset_prices
WHERE currency = 'usd'
ORDER BY symbol, "timestamp" DESC;

-- Create a view for multi-currency prices
CREATE OR REPLACE VIEW latest_prices_all_currencies AS
SELECT
    symbol,
    price as price_usd,
    price_eur,
    price_gbp,
    price_jpy,
    volume,
    market_cap,
    change_24h,
    "timestamp"
FROM asset_prices
WHERE currency = 'usd'
  AND "timestamp" = (
    SELECT MAX("timestamp")
    FROM asset_prices ap2
    WHERE ap2.symbol = asset_prices.symbol
  );
