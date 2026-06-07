# GEO Operations API — Frontend Integration Guide

Reference for building the **Next.js + Supabase** dashboard (or any BFF) that displays audit results. See [NEXTJS_SUPABASE_APP.md](NEXTJS_SUPABASE_APP.md) for full app architecture.

---

## Base URLs

| Environment | Base URL |
|-------------|----------|
| **Production** | `https://wc-geo-ops-production.up.railway.app` |
| **Local** | `http://127.0.0.1:8000` |

**Interactive docs:** `{BASE_URL}/docs` (Swagger UI)  
**OpenAPI JSON:** `{BASE_URL}/openapi.json`

**Root `/`** redirects to `/docs`.

---

## Security — read this first

| Rule | Detail |
|------|--------|
| **Never call Ops API from the browser with the API key** | `OPS_API_KEY` must stay on the server (Next.js Route Handlers / Server Actions). Exposing it in frontend JS is a credential leak. |
| **Recommended architecture** | Browser → **Next.js** (`/api/audits/*`) → Ops API with `Authorization: Bearer <OPS_API_KEY>` → persist in **Supabase** |
| **CORS** | Ops API is server-to-server only. Always proxy through Next.js. |

This document describes the **Ops API contract**. Your Next.js app wraps these endpoints and stores results in Supabase `audits` (see [NEXTJS_SUPABASE_APP.md](NEXTJS_SUPABASE_APP.md)).

---

## Authentication

All routes except `GET /health` require:

```http
Authorization: Bearer <OPS_API_KEY>
Content-Type: application/json
Accept: application/json
```

| Status | `detail` | UI action |
|--------|----------|-----------|
| `401` | Missing/invalid token | Show “Service unavailable”; log server-side |
| `503` | `OPS_API_KEY is not configured` | Ops misconfigured |

---

## Endpoints overview

| Method | Path | Auth | Tier | Behavior |
|--------|------|------|------|------------|
| `GET` | `/health` | No | — | Liveness check |
| `POST` | `/v1/audits/quick` | Yes | Free | Sync audit (~5–60s) |
| `POST` | `/v1/audits/full` | Yes | Paid | Async job enqueue |
| `GET` | `/v1/jobs/{job_id}` | Yes | Paid | Poll job status + report |

---

## 1. Health check

### `GET /health`

No request body.

**Response `200`**

```json
{
  "status": "ok",
  "service": "geo-ops-api",
  "version": "1.0.0"
}
```

Use for status indicators / ops monitoring only (not user-facing).

---

## 2. Quick audit (free tier)

### `POST /v1/audits/quick`

Synchronous. Scans homepage: crawlers, llms.txt, schema, citability. **No Claude.** Typical duration 5–15s (max 60s).

**Request body**

```json
{
  "url": "https://example.com/"
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `url` | string | Yes | `http(s)://` or bare domain; `www.` stripped |

**Response `200`**

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
      "citability_score": 55,
      "status_code": 200,
      "ai_crawler_status": {
        "GPTBot": "ALLOWED_BY_DEFAULT",
        "ClaudeBot": "NOT_MENTIONED"
      }
    },
    "quick_wins": [
      {
        "action": "Add llms.txt at site root",
        "impact": "Guides AI crawlers to key pages",
        "priority": "high"
      }
    ],
    "insights": [
      "Homepage has schema markup (Organization).",
      "Tier-1 AI crawlers are not explicitly blocked in robots.txt."
    ]
  },
  "duration_ms": 4200
}
```

**DB mapping (WC GEO)**

| Ops field | WC GEO column |
|-----------|---------------|
| `score.overall` | `audits.quick_score` |
| `summary` (full object) | `audits.quick_summary` (JSON) |

**Score tier labels** (`score.tier`)

| `tier` | Score range | Suggested UI label |
|--------|-------------|-------------------|
| `excellent` | 90–100 | Excellent |
| `good` | 75–89 | Good |
| `fair` | 60–74 | Fair |
| `poor` | 40–59 | Poor |
| `critical` | 0–39 | Critical |

**Quick win priorities:** `critical` | `high` | `medium`

**Errors**

| Status | Cause | UI |
|--------|-------|-----|
| `422` | Invalid URL | Inline validation on URL field |
| `502` | Site blocked / fetch failed | “Could not reach this website” |
| `504` | >60s timeout | “Scan timed out — try again” |

**UI flow**

1. User enters URL → show loading spinner (up to 60s).
2. On success → score ring + breakdown bars + quick wins list + insights.
3. Store `score.overall` and full `summary` via your backend.

---

## 3. Full audit (paid tier)

### `POST /v1/audits/full`

Asynchronous. Enqueues a background job (Claude + deep crawl). Returns immediately.

**Request body**

```json
{
  "url": "https://example.com/",
  "domain": "example.com",
  "client_ref": "audit-uuid-or-external-id"
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `url` | string | Yes | Target site |
| `domain` | string | No | Defaults to host from `url` |
| `client_ref` | string | No | Your audit/order ID for logging & webhooks |

**Response `202 Accepted`**

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "url": "https://example.com/",
  "domain": "example.com"
}
```

**Errors:** `401`, `422`, `503` (Redis down — full audits unavailable)

**UI flow**

1. On `202` → save `job_id`, show “Audit in progress…”
2. Poll `GET /v1/jobs/{job_id}` every **15s** (back off to 30s after 2 min)
3. Stop when `status` is `completed` or `failed`
4. Max wait ~5–10 min before showing “Taking longer than expected”

---

## 4. Job status (poll full audit)

### `GET /v1/jobs/{job_id}`

**Response `200` — job states**

| `status` | Meaning | `report` | `error` |
|----------|---------|----------|---------|
| `queued` | Waiting for worker | `null` | `null` |
| `processing` | Running | `null` | `null` |
| `completed` | Done | Full report object | `null` |
| `failed` | Error | `null` | Error message string |

**Example — in progress**

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "url": "https://example.com/",
  "domain": "example.com",
  "client_ref": "test-1",
  "created_at": "2026-06-07T02:45:03.531436+00:00",
  "completed_at": "",
  "duration_ms": null,
  "report": null,
  "error": null
}
```

**Example — completed**

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "url": "https://example.com/",
  "domain": "example.com",
  "client_ref": "test-1",
  "created_at": "2026-06-07T02:45:03.531436+00:00",
  "completed_at": "2026-06-07T02:46:00Z",
  "duration_ms": 53391,
  "report": { },
  "error": null
}
```

**Response `404`** — unknown or expired `job_id`

---

## 5. Full audit report shape (`report`)

When `status === "completed"`, `report` contains the paid deliverable. See [`examples/electron-srl.com-audit.json`](../examples/electron-srl.com-audit.json).

### Top-level fields

| Field | Type | UI section |
|-------|------|------------|
| `url` | string | Header |
| `brand_name` | string | Header |
| `date` | string (ISO date) | Header |
| `geo_score` | number 0–100 | Hero score |
| `scores` | object | Category breakdown |
| `platforms` | object | AI platform cards |
| `executive_summary` | string | Summary paragraph |
| `findings` | array | Issues list |
| `quick_wins` | array | Action plan (quick) |
| `medium_term` | array | Action plan (medium) |
| `strategic` | array | Action plan (strategic) |
| `crawler_access` | object | Crawler table |

### `scores` breakdown

```json
{
  "ai_citability": 18,
  "brand_authority": 15,
  "content_eeat": 35,
  "technical": 38,
  "schema": 8,
  "platform_optimization": 35
}
```

### `platforms` (per AI surface)

```json
{
  "Google AI Overviews": 25,
  "ChatGPT Web Search": 18,
  "Perplexity AI": 20,
  "Google Gemini": 12,
  "Bing Copilot": 28
}
```

### `findings[]`

```json
{
  "severity": "critical",
  "title": "Server Blocks All AI Crawlers (HTTP 403)",
  "description": "..."
}
```

**Severity badges:** `critical` (red) | `high` (orange) | `medium` (yellow)

### Action items (`quick_wins`, `medium_term`, `strategic`)

```json
{
  "action": "Add Organization JSON-LD schema on homepage",
  "impact": "+4 pts, improves all 5 platforms"
}
```

### `crawler_access`

```json
{
  "GPTBot": {
    "platform": "ChatGPT",
    "status": "BLOCKED (403)",
    "recommendation": "Whitelist immediately"
  }
}
```

---

## TypeScript types (frontend / BFF)

```typescript
export type ScoreTier =
  | "excellent"
  | "good"
  | "fair"
  | "poor"
  | "critical";

export type JobStatus =
  | "queued"
  | "processing"
  | "completed"
  | "failed";

export interface QuickAuditRequest {
  url: string;
}

export interface QuickAuditResponse {
  url: string;
  domain: string;
  score: {
    overall: number;
    breakdown: {
      technical_geo: number;
      citability: number;
      schema: number;
    };
    tier: ScoreTier;
  };
  summary: {
    tier: "free";
    metrics: Record<string, unknown>;
    quick_wins: Array<{
      action: string;
      impact: string;
      priority: "critical" | "high" | "medium";
    }>;
    insights: string[];
  };
  duration_ms: number;
}

export interface FullAuditRequest {
  url: string;
  domain?: string;
  client_ref?: string;
}

export interface FullAuditEnqueueResponse {
  job_id: string;
  status: "queued";
  url: string;
  domain: string;
}

export interface JobResponse {
  job_id: string;
  status: JobStatus;
  url: string;
  domain: string;
  client_ref: string;
  created_at: string;
  completed_at: string | null;
  duration_ms: number | null;
  report: FullAuditReport | null;
  error: string | null;
}

export interface FullAuditReport {
  url: string;
  brand_name: string;
  date: string;
  geo_score: number;
  scores: {
    ai_citability: number;
    brand_authority: number;
    content_eeat: number;
    technical: number;
    schema: number;
    platform_optimization: number;
  };
  platforms: Record<string, number>;
  executive_summary: string;
  findings: Array<{
    severity: "critical" | "high" | "medium";
    title: string;
    description: string;
  }>;
  quick_wins: Array<{ action: string; impact: string }>;
  medium_term: Array<{ action: string; impact: string }>;
  strategic: Array<{ action: string; impact: string }>;
  crawler_access: Record<
    string,
    { platform: string; status: string; recommendation: string }
  >;
}

export interface ApiError {
  detail: string;
}
```

---

## Example: BFF proxy (pseudo-code)

Frontend should call **your backend**, not Ops directly:

```typescript
// Frontend
const res = await fetch("/api/audit/quick", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ url: "https://loomod.com/" }),
});
const data: QuickAuditResponse = await res.json();
```

```php
// WC GEO backend (Guzzle) — server-side only
$client->post($opsBaseUrl . '/v1/audits/quick', [
    'headers' => [
        'Authorization' => 'Bearer ' . $opsApiKey,
        'Content-Type'  => 'application/json',
    ],
    'json' => ['url' => $url],
]);
```

---

## Polling helper (full audit)

```typescript
async function pollJob(
  fetchJob: (id: string) => Promise<JobResponse>,
  jobId: string,
  opts = { intervalMs: 15_000, maxAttempts: 40 }
): Promise<JobResponse> {
  for (let i = 0; i < opts.maxAttempts; i++) {
    const job = await fetchJob(jobId);
    if (job.status === "completed" || job.status === "failed") {
      return job;
    }
    await new Promise((r) => setTimeout(r, opts.intervalMs));
  }
  throw new Error("Audit timed out while polling");
}
```

---

## UI component map

| Screen | Data source | Key fields |
|--------|-------------|------------|
| URL scan input | User input | `url` |
| Free results hero | Quick audit | `score.overall`, `score.tier` |
| Breakdown chart | Quick audit | `score.breakdown` |
| Quick wins list | Quick audit | `summary.quick_wins` |
| Insights | Quick audit | `summary.insights` |
| Paid progress | Job poll | `status`, `duration_ms` |
| Full report hero | Full report | `geo_score`, `executive_summary` |
| Category scores | Full report | `scores` |
| Platform cards | Full report | `platforms` |
| Findings table | Full report | `findings` |
| Action plan tabs | Full report | `quick_wins`, `medium_term`, `strategic` |
| Crawler matrix | Full report | `crawler_access` |

---

## Error response format

All errors return FastAPI JSON:

```json
{
  "detail": "Human-readable message"
}
```

`detail` may be a string or validation array for `422`.

---

## Related docs

| Doc | Purpose |
|-----|---------|
| [GEO_OPERATIONS_BACKEND.md](../GEO_OPERATIONS_BACKEND.md) | Full API contract |
| [WC_GEO_INTEGRATION.md](WC_GEO_INTEGRATION.md) | PHP backend wiring |
| [wc-geo-parity.md](wc-geo-parity.md) | DB field mapping |
| [RAILWAY.md](../RAILWAY.md) | Production deploy |

---

## Changelog

| Version | API `version` field | Notes |
|---------|---------------------|-------|
| 1.0.0 | `geo-ops-api` | Initial: quick, full, jobs |
