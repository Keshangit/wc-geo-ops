# GEO Operations Backend — API Contract

HTTP API for WC GEO. All routes except health require `Authorization: Bearer <OPS_API_KEY>`.

Base URL example: `http://127.0.0.1:8000`

---

## GET /health

No authentication.

**Response 200**

```json
{
  "status": "ok",
  "service": "geo-ops-api",
  "version": "1.0.0"
}
```

---

## POST /v1/audits/quick

Free tier. Synchronous (~60s max). No Claude.

**Request**

```json
{
  "url": "https://example.com/"
}
```

**Response 200**

```json
{
  "url": "https://example.com/",
  "domain": "example.com",
  "score": {
    "overall": 62,
    "breakdown": {
      "technical_geo": 70,
      "citability": 55,
      "schema": 45
    },
    "tier": "fair"
  },
  "summary": {
    "tier": "free",
    "metrics": {
      "title": "Example Site",
      "has_schema": true,
      "schema_types": ["Organization"],
      "h1_count": 1,
      "word_count": 450,
      "llms_txt_score": 0,
      "llms_txt_exists": false,
      "crawler_access_score": 85,
      "tier1_blocked_count": 0,
      "citability_score": 55
    },
    "quick_wins": [
      {
        "action": "Add llms.txt",
        "impact": "Helps AI crawlers discover key pages",
        "priority": "high"
      }
    ],
    "insights": [
      "Homepage has Organization schema.",
      "All Tier-1 AI crawlers allowed in robots.txt."
    ]
  },
  "duration_ms": 4200
}
```

**Errors**

| Status | When |
|--------|------|
| 401 | Missing/invalid Bearer token |
| 422 | Invalid URL |
| 502 | Fetch failed (blocked, timeout, HTTP error) |
| 504 | Exceeded server timeout (default 60s) |

WC GEO stores `score.overall` → `audits.quick_score`, `summary` JSON → `audits.quick_summary`.

---

## POST /v1/audits/full

Paid tier. Enqueues async job.

**Request**

```json
{
  "url": "https://example.com/",
  "domain": "example.com",
  "client_ref": "audit-uuid-or-external-id"
}
```

**Response 202**

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "url": "https://example.com/",
  "domain": "example.com"
}
```

**Errors:** 401, 422, 503 (Redis unavailable)

---

## GET /v1/jobs/{job_id}

Poll full audit job.

**Response 200 (queued/processing)**

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "url": "https://example.com/",
  "domain": "example.com",
  "client_ref": "test-1",
  "created_at": "2026-06-04T12:00:00Z",
  "report": null,
  "error": null
}
```

**Response 200 (completed)**

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "url": "https://example.com/",
  "domain": "example.com",
  "client_ref": "test-1",
  "created_at": "2026-06-04T12:00:00Z",
  "completed_at": "2026-06-04T12:05:30Z",
  "duration_ms": 330000,
  "report": { },
  "error": null
}
```

`report` matches full audit JSON (see `examples/electron-srl.com-audit.json`).

**Response 200 (failed)**

```json
{
  "job_id": "...",
  "status": "failed",
  "error": "Anthropic API error: ...",
  "report": null
}
```

**Response 404** — unknown job_id

---

## Webhook (optional)

If `WC_GEO_WEBHOOK_URL` is set, worker POSTs on completion:

```json
{
  "job_id": "...",
  "status": "completed",
  "client_ref": "...",
  "domain": "example.com"
}
```

---

## 8. WC GEO integration (after Ops API works)

1. `.env`: `geoOps.enabled`, `geoOps.baseUrl`, `geoOps.apiKey` (= `OPS_API_KEY`)
2. `App\Services\GeoOpsClient` — Guzzle client for these endpoints
3. `Audit::quick()` → Ops quick endpoint
4. `FullAuditJob` → enqueue + poll Ops; PDF remains in PHP
