from __future__ import annotations

import logging
import time
from typing import Any

import requests

from api.integrations import geo_scripts
from api.services.scoring import (
    build_insights,
    build_quick_wins,
    citability_from_page,
    crawler_access_score,
    llms_txt_score,
    overall_quick_score,
    schema_score,
    score_tier_label,
    technical_geo_score,
)
from api.services.url_normalize import UrlValidationError, normalize_url

logger = logging.getLogger(__name__)


class QuickAuditFetchError(Exception):
    pass


def run_quick_audit(raw_url: str) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        url, domain = normalize_url(raw_url)
    except UrlValidationError:
        raise

    page = geo_scripts.fetch_page(url)
    if page.get("errors") and not page.get("status_code"):
        raise QuickAuditFetchError("; ".join(page["errors"]))

    status = page.get("status_code")
    if status is None or status >= 400:
        raise QuickAuditFetchError(
            f"Homepage returned HTTP {status or 'unknown'}"
        )

    robots = geo_scripts.fetch_robots_txt(url)
    llms = geo_scripts.validate_llmstxt(url)

    try:
        citability = geo_scripts.analyze_page_citability(url)
    except requests.RequestException as e:
        citability = {"error": str(e), "average_citability_score": 0}

    ai_status = robots.get("ai_crawler_status", {})
    crawl_score, tier1_blocked = crawler_access_score(ai_status)
    llms_score = llms_txt_score(llms)
    schema_pts = schema_score(page.get("structured_data", []))
    cit_pts = citability_from_page(citability)
    tech_pts = technical_geo_score(crawl_score, llms_score, page)
    overall = overall_quick_score(tech_pts, cit_pts, schema_pts)

    schema_types: list[str] = []
    for item in page.get("structured_data", []):
        t = item.get("@type")
        if isinstance(t, list):
            schema_types.extend(str(x) for x in t)
        elif t:
            schema_types.append(str(t))

    metrics: dict[str, Any] = {
        "title": page.get("title"),
        "has_schema": bool(page.get("structured_data")),
        "schema_types": list(dict.fromkeys(schema_types)),
        "h1_count": len(page.get("h1_tags") or []),
        "word_count": page.get("word_count", 0),
        "llms_txt_score": llms_score,
        "llms_txt_exists": llms.get("exists", False),
        "crawler_access_score": crawl_score,
        "tier1_blocked_count": tier1_blocked,
        "citability_score": cit_pts,
        "status_code": status,
        "ai_crawler_status": ai_status,
    }

    summary = {
        "tier": "free",
        "metrics": metrics,
        "quick_wins": build_quick_wins(metrics, ai_status),
        "insights": build_insights(metrics, ai_status),
    }

    duration_ms = int((time.perf_counter() - started) * 1000)
    logger.info(
        "quick_audit completed",
        extra={"url": url, "domain": domain, "duration_ms": duration_ms},
    )

    return {
        "url": url,
        "domain": domain,
        "score": {
            "overall": overall,
            "breakdown": {
                "technical_geo": tech_pts,
                "citability": cit_pts,
                "schema": schema_pts,
            },
            "tier": score_tier_label(overall),
        },
        "summary": summary,
        "duration_ms": duration_ms,
    }
