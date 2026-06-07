# WC GEO integration (Phase E)

Implement in the **WC GEO** PHP repository after Ops API passes contract tests.

## Environment

```env
geoOps.enabled = true
geoOps.baseUrl = http://127.0.0.1:8000
geoOps.apiKey = <same as OPS_API_KEY>
```

## GeoOpsClient (Guzzle)

| Method | Ops endpoint |
|--------|----------------|
| `quickAudit(string $url)` | `POST /v1/audits/quick` |
| `startFullAudit(string $url, ?string $domain, ?string $clientRef)` | `POST /v1/audits/full` |
| `getJob(string $jobId)` | `GET /v1/jobs/{job_id}` |

Headers: `Authorization: Bearer {apiKey}`, `Content-Type: application/json`, `Accept: application/json`.

## Controller / job changes

1. `app/Controllers/Api/Audit.php` — `quick()` calls `GeoOpsClient` when `geoOps.enabled`
2. `app/Jobs/FullAuditJob.php` — enqueue via Ops, poll until `completed`, store `report` JSON; PDF generation unchanged

## Rollout

Keep `geoOps.enabled = false` until golden JSON from Ops matches `GeoQuickAuditService` / `GeoFullAuditService` on the same test URLs.
