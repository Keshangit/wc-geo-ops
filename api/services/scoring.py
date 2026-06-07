"""Quick-audit scoring aligned with geo-seo-claude methodology."""

from __future__ import annotations  # noqa: I001

from typing import Any

TIER1_CRAWLERS = [
    "GPTBot",
    "OAI-SearchBot",
    "ChatGPT-User",
    "ClaudeBot",
    "anthropic-ai",
    "PerplexityBot",
]

BLOCKED_STATUSES = frozenset(
    {"BLOCKED", "BLOCKED_BY_WILDCARD", "PARTIALLY_BLOCKED"}
)


def score_tier_label(overall: int) -> str:
    if overall >= 90:
        return "excellent"
    if overall >= 75:
        return "good"
    if overall >= 60:
        return "fair"
    if overall >= 40:
        return "poor"
    return "critical"


def crawler_access_score(ai_crawler_status: dict[str, str]) -> tuple[int, int]:
    """Return (score 0-100, tier1_blocked_count)."""
    score = 100
    blocked = 0
    for crawler in TIER1_CRAWLERS:
        status = ai_crawler_status.get(crawler, "NOT_MENTIONED")
        if status in BLOCKED_STATUSES:
            score -= 15
            blocked += 1
    if not ai_crawler_status:
        score = 70
    return max(0, score), blocked


def llms_txt_score(validation: dict[str, Any]) -> int:
    if not validation.get("exists"):
        return 0
    if validation.get("format_valid"):
        if validation.get("link_count", 0) >= 5:
            return 100
        if validation.get("section_count", 0) >= 2:
            return 70
        return 50
    if validation.get("has_title") or validation.get("has_sections"):
        return 30
    return 10


def schema_score(structured_data: list[dict]) -> int:
    if not structured_data:
        return 0
    types: set[str] = set()
    for item in structured_data:
        t = item.get("@type")
        if isinstance(t, list):
            types.update(str(x) for x in t)
        elif t:
            types.add(str(t))
    score = 30
    priority = {
        "Organization",
        "LocalBusiness",
        "WebSite",
        "Product",
        "Article",
        "FAQPage",
    }
    if types & priority:
        score += 40
    if len(types) >= 2:
        score += 20
    if any(item.get("sameAs") for item in structured_data):
        score += 10
    return min(100, score)


def citability_from_page(citability_result: dict[str, Any]) -> int:
    if citability_result.get("error"):
        return 0
    avg = citability_result.get("average_citability_score", 0)
    return int(round(min(100, max(0, avg))))


def technical_geo_score(
    crawler_score: int,
    llms_score: int,
    page_data: dict[str, Any],
) -> int:
    base = int(crawler_score * 0.5 + llms_score * 0.2)
    tech = 30
    if page_data.get("title"):
        tech += 10
    if page_data.get("description"):
        tech += 10
    if page_data.get("canonical"):
        tech += 5
    if page_data.get("h1_tags"):
        tech += 10
    if page_data.get("status_code") == 200:
        tech += 15
    return min(100, int(base * 0.5 + tech * 0.5))


def overall_quick_score(
    technical_geo: int,
    citability: int,
    schema: int,
) -> int:
    return int(round(technical_geo * 0.4 + citability * 0.35 + schema * 0.25))


def build_quick_wins(
    metrics: dict[str, Any],
    ai_crawler_status: dict[str, str],
) -> list[dict[str, str]]:
    wins: list[dict[str, str]] = []

    blocked = [
        c
        for c in TIER1_CRAWLERS
        if ai_crawler_status.get(c) in BLOCKED_STATUSES
    ]
    if blocked:
        wins.append(
            {
                "action": f"Allow Tier-1 AI crawlers in robots.txt ({', '.join(blocked[:3])}{'...' if len(blocked) > 3 else ''})",
                "impact": "Unlocks AI search indexing",
                "priority": "critical",
            }
        )

    if not metrics.get("llms_txt_exists"):
        wins.append(
            {
                "action": "Add llms.txt at site root",
                "impact": "Guides AI crawlers to key pages",
                "priority": "high",
            }
        )

    if not metrics.get("has_schema"):
        wins.append(
            {
                "action": "Add Organization JSON-LD schema on homepage",
                "impact": "Improves entity recognition in AI answers",
                "priority": "high",
            }
        )

    if metrics.get("citability_score", 100) < 50:
        wins.append(
            {
                "action": "Add 134-167 word answer blocks with definitions and stats",
                "impact": "Increases likelihood of AI citations",
                "priority": "medium",
            }
        )

    if metrics.get("h1_count", 0) != 1:
        wins.append(
            {
                "action": "Use exactly one H1 on the homepage",
                "impact": "Clearer content hierarchy for crawlers",
                "priority": "medium",
            }
        )

    return wins[:6]


def build_insights(
    metrics: dict[str, Any],
    ai_crawler_status: dict[str, str],
) -> list[str]:
    insights: list[str] = []

    if metrics.get("has_schema"):
        types = metrics.get("schema_types") or []
        insights.append(
            f"Homepage has schema markup ({', '.join(types[:3]) or 'types detected'})."
        )
    else:
        insights.append("No JSON-LD structured data detected on the homepage.")

    blocked = sum(
        1
        for c in TIER1_CRAWLERS
        if ai_crawler_status.get(c) in BLOCKED_STATUSES
    )
    if blocked == 0:
        insights.append("Tier-1 AI crawlers are not explicitly blocked in robots.txt.")
    else:
        insights.append(
            f"{blocked} Tier-1 AI crawler(s) appear blocked or restricted in robots.txt."
        )

    if metrics.get("llms_txt_exists"):
        insights.append("llms.txt is present.")
    else:
        insights.append("No llms.txt file found.")

    cit = metrics.get("citability_score", 0)
    if cit >= 70:
        insights.append("Homepage content shows strong AI citability signals.")
    elif cit >= 40:
        insights.append("Homepage citability is moderate; answer blocks can be improved.")
    else:
        insights.append("Homepage content is weak for AI citation (catalog-style or thin).")

    return insights
