# Persistent Memory

## User Preferences
- Keep solutions practical and implementation-first.
- Track decisions so future chats stay consistent.
- Manual git commits (no auto-push).
- Prefers detailed explanations before implementation choices.

## Project Snapshot
- **Phase 1 COMPLETE**: Infrastructure + Data Layer fully operational
- Docker Compose running: PostgreSQL, n8n, ML API, MCP Server
- n8n workflows: market_data_ingestion, dead_letter_handler, daily_quality_check
- Data flowing: CoinGecko prices + news → ML sentiment → PostgreSQL
- MCP server running on port 8081

## Current Focus
- Phase 2: Dashboard (React + FastAPI) and Alerts (n8n + Slack)

## Next Steps
<!-- NEXT_STEPS_START -->
- Build React + FastAPI dashboard service
- Create n8n alert workflow for price spikes
- Configure Slack webhook for notifications
- Connect MCP to Claude Desktop (quick win)
<!-- NEXT_STEPS_END -->

## Key Technical Details
- **CoinGecko API**: Using for prices and news (CryptoPanic had CSRF issues)
- **MCP Port**: 8081 (8080 was conflicting)
- **Tracked Assets**: bitcoin, ethereum, solana
- **CryptoPanic API Key**: 798cb257a5f7228cab2040bfeed99fbf7a8b5897 (unused, kept for reference)

## Session Log
<!-- SESSION_LOG_START -->
- 2026-03-20: Bootstrapped persistent memory and workflow files.
- 2026-03-20 23:46: Validated starter workflow
- 2026-03-21: Completed Phase 1 - all n8n workflows functional, data ingestion working
- 2026-03-21: Created docs/PHASE_2_ROADMAP.md with implementation guides
- 2026-03-21: Starting Phase 2 - Dashboard (React+FastAPI) + Alerts (n8n+Slack)
<!-- SESSION_LOG_END -->
