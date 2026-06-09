# Railway setup

Deploy settings are **not** in `railway.toml` so each service can be configured separately in the Railway dashboard.

## Services (Backend environment)

| Service | Start command | Health check | Public domain |
|---------|---------------|--------------|---------------|
| **wc-geo-ops (API)** | `python -m api` | Path: `/health`, timeout 120s | Yes |
| **wc-geo-ops-worker** | `python -m api.workers.full_worker` | **Disabled** | No |
| **Redis** | (Railway plugin) | — | No |

`api/__main__.py` reads `PORT` from the environment (Railway injects this automatically).

### API service — Settings → Deploy

- **Custom Start Command:** `python -m api`
- **Healthcheck Path:** `/health`
- **Healthcheck Timeout:** `120`

### Worker service — Settings → Deploy

- **Custom Start Command:** `python -m api.workers.full_worker`  
  (or `./scripts/start-worker.sh`)
- **Healthcheck:** disabled or path left empty — the worker has no HTTP server

After deploy, worker logs must show:

```text
*** Listening on geo_full_audits...
```

Not `Uvicorn running on http://0.0.0.0:8080`.

## Variables

Set on **both** API and worker (not in the Dockerfile):

| Variable | API | Worker | Notes |
|----------|-----|--------|-------|
| `OPS_API_KEY` | Yes | Yes | |
| `ANTHROPIC_API_KEY` | Optional | **Yes** | Worker runs Claude for full reports |
| `REDIS_URL` | **Yes** | **Yes** | Full URL: `redis://default:pass@host:6379` or `${{Redis.REDIS_URL}}` |

**Wrong:** `redis-backend-daa9.up.railway.app` (hostname only — causes 500 on full audit)

## If deploy fails with `'$PORT' is not a valid integer`

A stale **Custom Start Command** like:

```text
python -m uvicorn api.main:app --host 0.0.0.0 --port $PORT
```

passes the literal string `$PORT` (no shell expansion). Clear it and use `python -m api` instead.

## Verify full audit

```bash
# Enqueue (expect 202 + job_id)
curl -s -X POST https://wc-geo-ops-production.up.railway.app/v1/audits/full \
  -H "Authorization: Bearer $OPS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com/","domain":"example.com"}'

# Poll job (expect queued → processing → completed)
curl -s "https://wc-geo-ops-production.up.railway.app/v1/jobs/JOB_ID" \
  -H "Authorization: Bearer $OPS_API_KEY"
```
