import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.config import get_settings
from api.main import app

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("OPS_API_KEY", "test-secret-key")
    get_settings.cache_clear()
    with TestClient(app) as c:
        yield c
    get_settings.cache_clear()


def test_health_no_auth(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["service"] == "geo-ops-api"


def test_quick_requires_auth(client):
    r = client.post("/v1/audits/quick", json={"url": "https://example.com"})
    assert r.status_code == 401


def test_quick_invalid_url(client):
    r = client.post(
        "/v1/audits/quick",
        json={"url": "not-a-url"},
        headers={"Authorization": "Bearer test-secret-key"},
    )
    assert r.status_code == 422


def test_quick_response_shape(client):
    mock_page = {
        "url": "https://example.com/",
        "status_code": 200,
        "title": "Example",
        "description": "Desc",
        "canonical": "https://example.com/",
        "h1_tags": ["Hello"],
        "word_count": 200,
        "structured_data": [{"@type": "Organization", "name": "Example"}],
        "errors": [],
    }
    mock_robots = {
        "ai_crawler_status": {
            "GPTBot": "NOT_MENTIONED",
            "ClaudeBot": "NOT_MENTIONED",
            "PerplexityBot": "NOT_MENTIONED",
            "OAI-SearchBot": "NOT_MENTIONED",
            "ChatGPT-User": "NOT_MENTIONED",
            "anthropic-ai": "NOT_MENTIONED",
        }
    }
    mock_llms = {"exists": False, "format_valid": False}
    mock_citability = {"average_citability_score": 45.0}

    with (
        patch("api.services.quick_audit.geo_scripts.fetch_page", return_value=mock_page),
        patch(
            "api.services.quick_audit.geo_scripts.fetch_robots_txt",
            return_value=mock_robots,
        ),
        patch(
            "api.services.quick_audit.geo_scripts.validate_llmstxt",
            return_value=mock_llms,
        ),
        patch(
            "api.services.quick_audit.geo_scripts.analyze_page_citability",
            return_value=mock_citability,
        ),
    ):
        r = client.post(
            "/v1/audits/quick",
            json={"url": "https://example.com/"},
            headers={"Authorization": "Bearer test-secret-key"},
        )

    assert r.status_code == 200
    data = r.json()

    minimal = json.loads((FIXTURES / "quick_audit_minimal.json").read_text())
    for key in minimal:
        assert key in data, f"missing top-level key {key}"
    assert "overall" in data["score"]
    assert "breakdown" in data["score"]
    assert data["summary"]["tier"] == "free"
    assert "metrics" in data["summary"]
    assert "quick_wins" in data["summary"]
    assert "insights" in data["summary"]
    assert data["domain"] == "example.com"


def test_scoring_unit():
    from api.services.scoring import (
        crawler_access_score,
        overall_quick_score,
        score_tier_label,
    )

    score, blocked = crawler_access_score(
        {"GPTBot": "BLOCKED", "ClaudeBot": "ALLOWED"}
    )
    assert blocked == 1
    assert score == 85

    overall = overall_quick_score(70, 50, 40)
    assert 40 <= overall <= 80
    assert score_tier_label(28) == "critical"


def test_url_normalize():
    from api.services.url_normalize import normalize_url

    url, domain = normalize_url("www.example.com")
    assert domain == "example.com"
    assert url.startswith("https://")
