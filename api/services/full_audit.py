from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

import httpx

from api.config import get_settings
from api.integrations import geo_scripts
from api.services.url_normalize import normalize_url

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]


def collect_discovery(url: str) -> dict[str, Any]:
    settings = get_settings()
    page = geo_scripts.fetch_page(url)
    robots = geo_scripts.fetch_robots_txt(url)
    llms = geo_scripts.validate_llmstxt(url)

    try:
        citability = geo_scripts.analyze_page_citability(url)
    except Exception as e:
        citability = {"error": str(e)}

    sitemap_pages = geo_scripts.crawl_sitemap(
        url, max_pages=settings.full_sitemap_max_pages
    )
    sample_urls = [u for u in sitemap_pages if u.rstrip("/") != url.rstrip("/")][
        : settings.full_sample_pages
    ]
    sampled_pages = []
    for sample_url in sample_urls:
        try:
            sampled_pages.append(geo_scripts.fetch_page(sample_url))
        except Exception as e:
            sampled_pages.append({"url": sample_url, "errors": [str(e)]})

    return {
        "homepage": page,
        "robots": robots,
        "llms": llms,
        "citability": citability,
        "sitemap_page_count": len(sitemap_pages),
        "sitemap_sample": sitemap_pages[:10],
        "sampled_pages": sampled_pages,
    }


def _load_prompt_excerpt(max_chars: int = 12000) -> str:
    parts: list[str] = []
    for rel in (
        "skills/geo-audit/SKILL.md",
        "skills/geo-report/SKILL.md",
    ):
        path = _REPO_ROOT / rel
        if path.exists():
            text = path.read_text(encoding="utf-8")
            parts.append(f"--- {rel} ---\n{text[: max_chars // 2]}")
    return "\n\n".join(parts)[:max_chars]


def generate_report_with_claude(
    url: str,
    domain: str,
    discovery: dict[str, Any],
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured")

    system = (
        "You are a GEO (Generative Engine Optimization) auditor. "
        "Respond with a single JSON object only — no markdown fences. "
        "Match this structure: url, brand_name, date (ISO date), geo_score (0-100), "
        "scores (ai_citability, brand_authority, content_eeat, technical, schema, "
        "platform_optimization), platforms (object with 5 AI platform scores), "
        "executive_summary (string), findings (array of severity/title/description), "
        "quick_wins, medium_term, strategic (arrays of action/impact objects), "
        "crawler_access (object per bot). Base scores on the provided discovery data.\n\n"
        + _load_prompt_excerpt()
    )

    user_payload = {
        "url": url,
        "domain": domain,
        "discovery": discovery,
    }

    try:
        import anthropic
    except ImportError as e:
        raise RuntimeError("anthropic package not installed") from e

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=settings.anthropic_max_tokens,
        system=system,
        messages=[
            {
                "role": "user",
                "content": json.dumps(user_payload, default=str)[:100000],
            }
        ],
    )

    text = ""
    for block in message.content:
        if hasattr(block, "text"):
            text += block.text

    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(
            lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        )

    report = json.loads(text)
    if "url" not in report:
        report["url"] = url
    if "geo_score" not in report and "scores" in report:
        scores = report["scores"]
        if isinstance(scores, dict):
            vals = [v for v in scores.values() if isinstance(v, (int, float))]
            if vals:
                report["geo_score"] = int(sum(vals) / len(vals))
    return report


def run_full_audit_job(
    job_id: str,
    raw_url: str,
    domain: str | None,
    client_ref: str | None,
) -> None:
    from api.services.job_store import update_job

    started = time.perf_counter()
    extra = {"job_id": job_id, "client_ref": client_ref or "", "domain": domain or ""}
    logger.info("full_audit started", extra=extra)

    update_job(job_id, status="processing")

    try:
        url, normalized_domain = normalize_url(raw_url)
        if domain:
            normalized_domain = domain

        discovery = collect_discovery(url)
        report = generate_report_with_claude(url, normalized_domain, discovery)

        duration_ms = int((time.perf_counter() - started) * 1000)
        completed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        update_job(
            job_id,
            status="completed",
            report=report,
            error="",
            completed_at=completed_at,
            duration_ms=duration_ms,
        )
        logger.info(
            "full_audit completed",
            extra={**extra, "duration_ms": duration_ms, "status": "completed"},
        )
        _maybe_webhook(job_id, "completed", normalized_domain, client_ref)

    except Exception as e:
        duration_ms = int((time.perf_counter() - started) * 1000)
        update_job(
            job_id,
            status="failed",
            error=str(e),
            duration_ms=duration_ms,
        )
        logger.exception(
            "full_audit failed",
            extra={**extra, "duration_ms": duration_ms, "status": "failed"},
        )
        _maybe_webhook(job_id, "failed", domain or "", client_ref)


def _maybe_webhook(
    job_id: str,
    status: str,
    domain: str,
    client_ref: str | None,
) -> None:
    url = get_settings().wc_geo_webhook_url
    if not url:
        return
    try:
        httpx.post(
            url,
            json={
                "job_id": job_id,
                "status": status,
                "client_ref": client_ref,
                "domain": domain,
            },
            timeout=10.0,
        )
    except Exception as e:
        logger.warning("webhook failed: %s", e)
