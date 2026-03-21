# n8n Workflow Strategy (Phase 1)

## Goal
Automate hourly ingestion of market prices and news, enrich news with sentiment, and persist normalized data to PostgreSQL.

## Recommended Workflow Shape
1. **Cron Trigger (Every Hour)**
2. **HTTP Request - CoinGecko Prices**
3. **HTTP Request - News Feed/API**
4. **Function Node - Normalize Payloads**
5. **HTTP Request - ML API Sentiment Endpoint**
6. **Merge Node - Join News + Sentiment**
7. **PostgreSQL Node - Insert `asset_prices`**
8. **PostgreSQL Node - Insert `market_news`**
9. **IF/Alert Node - Failure Handling (Slack/Email/Discord)**

## Node-Level Notes
- **CoinGecko node**:
  - Endpoint example: `https://api.coingecko.com/api/v3/simple/price`
  - Request `ids` and `vs_currencies` for your tracked assets.
  - Map symbol/price/volume/timestamp in a Function node.

- **News node**:
  - Start with RSS feeds or a public API (e.g., CryptoPanic/NewsAPI if available).
  - Extract `headline`, `source`, `published timestamp`, and optional `url`.

- **Sentiment node**:
  - POST to `http://ml-api:8000/v1/sentiment/headlines`.
  - Body:
    ```json
    {
      "headlines": ["headline 1", "headline 2"]
    }
    ```
  - Store returned `normalized_score` as `ai_sentiment_score`.

- **Database writes**:
  - Use two dedicated Postgres nodes (one table each).
  - Prefer batched inserts for throughput.
  - Use unique key constraints to avoid duplicate inserts when jobs retry.

## Reliability Best Practices
- Enable workflow retries with exponential backoff on HTTP nodes.
- Route failed executions to a dead-letter workflow.
- Keep payload sizes bounded (chunk headlines when very large).
- Add a daily quality-check workflow (null score rate, stale symbols, missing rows).
