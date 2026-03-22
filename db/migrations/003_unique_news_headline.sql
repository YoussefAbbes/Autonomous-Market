-- Migration: Add unique constraint on market_news headline
-- Date: 2026-03-22
-- Purpose: Prevent duplicate news articles from being inserted

-- Clean up any existing duplicates (keep earliest record per headline)
DELETE FROM market_news
WHERE id NOT IN (
    SELECT MIN(id)
    FROM market_news
    GROUP BY headline
);

-- Add unique constraint on headline column
ALTER TABLE market_news ADD CONSTRAINT unique_headline UNIQUE (headline);

-- Note: The n8n workflow Insert News node should use "onConflict": "nothing"
-- to silently skip duplicates instead of failing
