# Railway setup

## If deploy fails with `'$PORT' is not a valid integer`

Railway dashboard **Custom Start Command** overrides the Dockerfile. A stale command like:

```text
python -m uvicorn api.main:app --host 0.0.0.0 --port $PORT
```

passes the literal string `$PORT` (no shell expansion) and the app never starts.

### Fix (required once)

1. Railway → **wc-geo-ops** → **Settings** → **Deploy**
2. **Delete / clear** the **Custom Start Command** field entirely  
   — or click **Clear start command** in the deployment diagnosis
3. Redeploy

The repo sets the correct command via `railway.toml`:

```text
python -m api
```

`api/__main__.py` reads `PORT` from the environment (Railway injects this automatically).

## Variables

Set in Railway **Variables** (not in the Dockerfile):

- `OPS_API_KEY`
- `ANTHROPIC_API_KEY` (full audits)
- `REDIS_URL` (full audits)

## Full audit worker

Add a **second** Railway service from the same repo:

**Start command:** `python -m api.workers.full_worker`

Same variables + Redis plugin.
