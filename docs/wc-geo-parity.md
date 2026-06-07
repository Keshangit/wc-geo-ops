# WC GEO parity notes

Maps Ops API output to expected WC GEO PHP behavior when PHP sources are available locally.

## Quick audit (`GeoQuickAuditService`)

| Ops field | WC GEO column / usage |
|-----------|----------------------|
| `score.overall` | `audits.quick_score` |
| `summary` (full object) | `audits.quick_summary` (JSON) |
| `summary.tier` | Always `"free"` for Ops quick |

Quick breakdown uses three sub-scores (not full 6-category audit):

- `technical_geo` — crawler access, llms.txt, homepage technical signals
- `citability` — homepage citability average
- `schema` — structured data presence and richness

## Robots (`RobotsAnalyzer`)

Tier-1 bots (must align with `scripts/fetch_page.py`):

GPTBot, OAI-SearchBot, ChatGPT-User, ClaudeBot, anthropic-ai, PerplexityBot

Statuses: `BLOCKED`, `PARTIALLY_BLOCKED`, `ALLOWED`, `BLOCKED_BY_WILDCARD`, `NOT_MENTIONED`, `NO_ROBOTS_TXT`

## Discovery (`GeoDiscoveryService`)

| Mode | Pages |
|------|-------|
| Quick | Homepage only (Ops implementation) |
| Full | Sitemap up to `FULL_SITEMAP_MAX_PAGES`, sample `FULL_SAMPLE_PAGES` inner pages |

## Full audit (`GeoFullAuditService` / `FullAuditJob`)

Job states: `queued` → `processing` → `completed` | `failed`

Report shape: see `examples/electron-srl.com-audit.json` and `GEO_OPERATIONS_BACKEND.md`.
