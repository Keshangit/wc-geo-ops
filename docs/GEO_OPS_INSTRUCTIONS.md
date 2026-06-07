# GEO Operations Backend — Setup

See [GEO_OPERATIONS_BACKEND.md](../GEO_OPERATIONS_BACKEND.md) for the API contract and [wc-geo-parity.md](wc-geo-parity.md) for PHP field mapping.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r api/requirements.txt
cp .env.example .env
# Edit OPS_API_KEY in .env

uvicorn api.main:app --reload --port 8000
```

## Full audit (Redis + worker)

Full audit is **async**: `POST /v1/audits/full` returns `202` + `job_id`. Poll `GET /v1/jobs/{job_id}` until `status` is `completed` or `failed`.

```bash
brew services start redis   # or docker run -d -p 6379:6379 redis:7-alpine

# Terminal 2 — worker (macOS: use module runner to avoid fork crashes)
source .venv/bin/activate
python -m api.workers.full_worker

# Linux / manual rq CLI:
# OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES rq worker geo_full_audits --url redis://127.0.0.1:6379/0
```

```bash
# Enqueue
curl -s -X POST http://127.0.0.1:8000/v1/audits/full \
  -H "Authorization: Bearer $OPS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://loomod.com/","domain":"loomod.com","client_ref":"1"}'

# Poll (replace JOB_ID)
curl -s http://127.0.0.1:8000/v1/jobs/JOB_ID \
  -H "Authorization: Bearer $OPS_API_KEY" | python -m json.tool
```

## Test quick audit

```bash
export OPS_API_KEY=your-key
curl -s -X POST http://127.0.0.1:8000/v1/audits/quick \
  -H "Authorization: Bearer $OPS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com/"}' | python -m json.tool
```

WC GEO integration checklist: [WC_GEO_INTEGRATION.md](WC_GEO_INTEGRATION.md)
