"""
The production boot guard (D1 NFR-09, D7 DEC-010).

This guard is what keeps the insecure-default mitigations honest: without it a
deployment could silently run with the published JWT secret or demo seeding.
"""
import pytest
from app.config import settings
from app.main import _check_production_safety


@pytest.fixture
def prod(monkeypatch):
    """Production environment with every setting safe, so each test can spoil one."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "JWT_SECRET", "a-real-and-unique-production-secret")
    monkeypatch.setattr(settings, "ALLOW_UNVERIFIED_GOOGLE_TOKENS", False)
    monkeypatch.setattr(settings, "CORS_ORIGINS", "https://koshi.example.com")
    monkeypatch.setattr(settings, "SEED_DEMO_DATA", False)
    return monkeypatch


def test_safe_production_config_starts(prod):
    _check_production_safety()  # must not raise


@pytest.mark.parametrize("attr,bad_value,expected", [
    ("JWT_SECRET", settings.DEV_JWT_SECRET, "JWT_SECRET"),
    ("ALLOW_UNVERIFIED_GOOGLE_TOKENS", True, "ALLOW_UNVERIFIED_GOOGLE_TOKENS"),
    ("CORS_ORIGINS", "*", "CORS_ORIGINS"),
    ("SEED_DEMO_DATA", True, "SEED_DEMO_DATA"),
])
def test_each_insecure_default_blocks_startup(prod, attr, bad_value, expected):
    prod.setattr(settings, attr, bad_value)
    with pytest.raises(RuntimeError) as exc:
        _check_production_safety()
    assert expected in str(exc.value)


def test_development_is_exempt(monkeypatch):
    """All four defaults are fine locally; the guard must not fire."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(settings, "JWT_SECRET", settings.DEV_JWT_SECRET)
    monkeypatch.setattr(settings, "ALLOW_UNVERIFIED_GOOGLE_TOKENS", True)
    monkeypatch.setattr(settings, "CORS_ORIGINS", "*")
    monkeypatch.setattr(settings, "SEED_DEMO_DATA", True)
    _check_production_safety()  # must not raise
