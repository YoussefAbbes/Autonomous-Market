# Decisions Log

Use this file to record major decisions and why they were made.

## Entries
- 2026-03-20: Introduced persistent memory workflow files (`memory.md`, `TASK_BOARD.md`, `SYSTEM.md`) to keep context across new chats.

- 2026-03-20 23:46: Use markdown-based persistent memory with marker sections

- 2026-03-21: **CoinGecko over CryptoPanic** - CryptoPanic API had CSRF verification issues (403 errors requiring Referer header). CoinGecko provides both prices AND news in a single, reliable API.

- 2026-03-21: **MCP Server port 8081** - Port 8080 was conflicting with another service on the system. Changed to 8081 in .env and docker-compose.yml.

- 2026-03-21: **Removed Python type annotations from MCP functions** - The MCP library had issues with `dict[str, Any]` return type annotations causing TypeError. Removed all type hints from `get_market_forecast` function.

- 2026-03-21: **ON CONFLICT DO NOTHING for idempotent inserts** - Added to both Insert Prices and Insert News n8n nodes to handle duplicate data gracefully.

- 2026-03-21: **Dashboard: React + FastAPI over Streamlit** - User chose production-quality stack for better customization and mobile-responsive design.

- 2026-03-21: **Alerts: n8n workflow over Python service** - Simpler approach using existing infrastructure. Slack as notification channel.

- 2026-03-21: **Hardcoded config in n8n workflows** - n8n Variables feature requires Pro plan. Replaced all `$vars` references with hardcoded values (Slack webhook URL, tracked assets, news API URL).
