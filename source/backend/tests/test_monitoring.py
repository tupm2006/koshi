"""Operations surface: health reports the database, /metrics is not public, ids stay out of labels."""
import pytest

from app.config import settings
from app.services import monitoring
from app.services.ai_service import AIFeature, AIService


@pytest.fixture(autouse=True)
def _fresh_metrics():
    monitoring.reset()
    yield
    monitoring.reset()


def test_health_checks_the_database(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["database"] == "ok"


def test_every_response_carries_a_request_id(client):
    r = client.get("/api/health")
    assert len(r.headers["X-Request-ID"]) >= 8


def test_supplied_request_id_is_kept_only_when_plain(client):
    assert client.get("/api/health", headers={"X-Request-ID": "abc-123"}).headers["X-Request-ID"] == "abc-123"
    assert client.get("/api/health", headers={"X-Request-ID": "x y;z"}).headers["X-Request-ID"] != "x y;z"
    assert client.get("/api/health", headers={"X-Request-ID": "a" * 65}).headers["X-Request-ID"] != "a" * 65


def test_metrics_open_in_development_without_token(client, monkeypatch):
    monkeypatch.setattr(settings, "METRICS_TOKEN", "")
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    client.get("/api/health")
    r = client.get("/api/metrics")
    assert r.status_code == 200
    assert 'koshi_http_requests_total{method="GET",route="/api/health",status="200"} 1' in r.text


def test_metrics_hidden_in_production_without_token(client, monkeypatch):
    monkeypatch.setattr(settings, "METRICS_TOKEN", "")
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    assert client.get("/api/metrics").status_code == 404


def test_metrics_require_the_configured_token(client, monkeypatch):
    monkeypatch.setattr(settings, "METRICS_TOKEN", "s3cret")
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    assert client.get("/api/metrics").status_code == 404
    assert client.get("/api/metrics", headers={"Authorization": "Bearer wrong"}).status_code == 404
    assert client.get("/api/metrics", headers={"Authorization": "Bearer s3cret"}).status_code == 200


def test_routes_are_labelled_by_template_not_by_id(client, pm_auth_headers, monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(settings, "METRICS_TOKEN", "")
    client.get("/api/tasks/987654", headers=pm_auth_headers)
    text = client.get("/api/metrics").text
    assert "987654" not in text
    assert "{task_id}" in text


@pytest.mark.asyncio
async def test_ai_answers_are_counted_by_tier(monkeypatch):
    async def fake(cls, feature, system, user):
        from app.services.ai_service import AITier
        return "x", AITier.DETERMINISTIC
    monkeypatch.setattr(AIService, "_cascade", classmethod(fake))
    await AIService._call_llm(AIFeature.WEEKLY_SUMMARY, "s", "u")
    assert 'koshi_ai_answers_total{feature="' in monitoring.render()
    assert 'tier="fallback"} 1' in monitoring.render()
