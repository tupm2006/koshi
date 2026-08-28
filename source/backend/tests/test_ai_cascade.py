"""
Provenance tests for the 3-tier AI cascade (D5 GAP-04).

The existing AI tests assert response *shape*, which the deterministic fallback
satisfies perfectly — so an expired API key, an unreachable Ollama, or a total
outage left the whole suite green while every user silently received canned
Vietnamese text instead of analysis.

These tests assert *which tier answered*. They are the only tests in the repo
that can tell a working AI deployment from a broken one.

Each tier is mocked at the `httpx.AsyncClient.post` boundary rather than by
patching `AIService` methods: patching the thing under test would prove only
that the mock works, and would not notice the URL, headers or payload drifting.
"""
import json
import logging
import pytest
import httpx

from app.services.ai_service import AIService, AIFeature, AITier
from app.config import settings


# --------------------------------------------------------------------------
# Fake transports
# --------------------------------------------------------------------------

def openai_reply(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}]}


def ollama_native_reply(content: str) -> dict:
    """Ollama's own /api/chat shape, which is not the OpenAI one."""
    return {"message": {"content": content}}


class FakeResponse:
    def __init__(self, status_code: int, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class Router:
    """
    Stands in for `httpx.AsyncClient.post` and routes by URL.

    Records every call so a test can assert what was actually sent — and, just
    as importantly, that a tier was *not* attempted.
    """

    def __init__(self, cloud=None, ollama=None):
        self.cloud = cloud
        self.ollama = ollama
        self.calls = []

    async def __call__(self, url, **kwargs):
        self.calls.append({"url": url, **kwargs})
        handler = self.ollama if "11434" in str(url) or "ollama" in str(url) else self.cloud
        if handler is None:
            raise httpx.ConnectError(f"nothing listening on {url}")
        if isinstance(handler, Exception):
            raise handler
        return handler

    @property
    def urls(self):
        return [c["url"] for c in self.calls]


@pytest.fixture
def route(monkeypatch):
    """Install a Router over httpx, and give tier 1 a key unless told otherwise."""
    def _install(cloud=None, ollama=None, api_key="test-key"):
        monkeypatch.setattr(settings, "AI_API_KEY", api_key)
        monkeypatch.setattr(settings, "AI_API_URL", "https://api.openai.com/v1/chat/completions")
        monkeypatch.setattr(settings, "AI_MODEL_NAME", "gpt-4o-mini")
        monkeypatch.setattr(settings, "OLLAMA_URL", "http://localhost:11434/v1/chat/completions")
        monkeypatch.setattr(settings, "OLLAMA_MODEL", "qwen2.5:7b")
        router = Router(cloud=cloud, ollama=ollama)
        monkeypatch.setattr(httpx.AsyncClient, "post", lambda self, url, **kw: router(url, **kw))
        return router
    return _install


async def call(feature=AIFeature.WEEKLY_SUMMARY):
    return await AIService._call_llm(feature, "system", "user")


# --------------------------------------------------------------------------
# Tier 1 — configured cloud endpoint
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tier1_answers_when_a_key_is_configured(route):
    router = route(cloud=FakeResponse(200, openai_reply("real analysis")))

    text, tier = await call()

    assert tier is AITier.CLOUD
    assert text == "real analysis"
    assert router.urls == ["https://api.openai.com/v1/chat/completions"]


@pytest.mark.asyncio
async def test_tier1_is_skipped_entirely_without_a_key(route):
    # No key means no request at all — not a request that fails. A deployment
    # that forgot the key must not be sending prompts to an unauthenticated
    # endpoint.
    router = route(cloud=FakeResponse(200, openai_reply("should not be used")),
                   ollama=FakeResponse(200, openai_reply("local")), api_key="")

    text, tier = await call()

    assert tier is AITier.OLLAMA
    assert text == "local"
    assert all("openai" not in u for u in router.urls)


@pytest.mark.asyncio
async def test_tier1_sends_the_key_model_and_prompts(route):
    router = route(cloud=FakeResponse(200, openai_reply("ok")))

    await AIService._call_llm(AIFeature.ASSIGNMENT, "SYS", "USR")

    sent = router.calls[0]
    assert sent["headers"]["Authorization"] == "Bearer test-key"
    assert sent["json"]["model"] == "gpt-4o-mini"
    assert sent["json"]["messages"] == [
        {"role": "system", "content": "SYS"},
        {"role": "user", "content": "USR"},
    ]
    # Low temperature: these are extraction tasks, not creative ones.
    assert sent["json"]["temperature"] == 0.2


@pytest.mark.parametrize("status", [401, 429, 500, 503])
@pytest.mark.asyncio
async def test_tier1_http_error_falls_through_to_tier2(route, status):
    # 401 is the one that matters in practice: a revoked key. It must degrade,
    # and it must be visible as a degradation rather than as success.
    router = route(cloud=FakeResponse(status, {}),
                   ollama=FakeResponse(200, openai_reply("local")))

    text, tier = await call()

    assert tier is AITier.OLLAMA
    assert text == "local"
    assert len(router.calls) == 2


@pytest.mark.asyncio
async def test_tier1_non_200_is_rejected_even_with_a_well_formed_body(route):
    # The parametrised test above sends an empty body, so a mutation removing
    # the status check still fell through — on the KeyError, not on the status.
    # A gateway or a quota error can return a perfectly shaped payload with a
    # non-200 code, and that must not be served as an answer.
    route(cloud=FakeResponse(503, openai_reply("stale cached answer")),
          ollama=FakeResponse(200, openai_reply("local")))

    text, tier = await call()

    assert tier is AITier.OLLAMA
    assert text == "local"


@pytest.mark.asyncio
async def test_tier1_timeout_falls_through_to_tier2(route):
    router = route(cloud=httpx.ReadTimeout("too slow"),
                   ollama=FakeResponse(200, openai_reply("local")))

    _, tier = await call()

    assert tier is AITier.OLLAMA


@pytest.mark.asyncio
async def test_tier1_malformed_body_falls_through(route):
    # 200 with a body that is not the expected shape. The `except` around the
    # whole block is what catches this; without it the KeyError would escape
    # and the cascade would not be a cascade.
    router = route(cloud=FakeResponse(200, {"unexpected": "shape"}),
                   ollama=FakeResponse(200, openai_reply("local")))

    _, tier = await call()

    assert tier is AITier.OLLAMA


# --------------------------------------------------------------------------
# Tier 2 — local Ollama
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tier2_accepts_the_openai_compatible_shape(route):
    route(cloud=None, ollama=FakeResponse(200, openai_reply("from ollama")))

    text, tier = await call()

    assert (text, tier) == ("from ollama", AITier.OLLAMA)


@pytest.mark.asyncio
async def test_tier2_accepts_ollamas_native_shape(route):
    # Ollama answers differently depending on which endpoint is configured;
    # both spellings must work or a valid local model silently does nothing.
    route(cloud=None, ollama=FakeResponse(200, ollama_native_reply("native")))

    text, tier = await call()

    assert (text, tier) == ("native", AITier.OLLAMA)


@pytest.mark.asyncio
async def test_tier2_sends_the_configured_model_without_streaming(route):
    router = route(cloud=None, ollama=FakeResponse(200, openai_reply("x")))

    await call()

    sent = router.calls[-1]
    assert sent["json"]["model"] == "qwen2.5:7b"
    # Streaming would return chunks the parser cannot read.
    assert sent["json"]["stream"] is False


@pytest.mark.asyncio
async def test_tier2_unrecognised_shape_falls_through_to_tier3(route):
    route(cloud=None, ollama=FakeResponse(200, {"neither": "shape"}))

    _, tier = await call()

    assert tier is AITier.DETERMINISTIC


# --------------------------------------------------------------------------
# Tier 3 — deterministic fallback
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tier3_answers_when_nothing_is_reachable(route):
    # This is the state CI runs in, and — until this file existed — the state
    # every other AI test was unknowingly asserting against.
    route(cloud=None, ollama=None)

    text, tier = await call()

    assert tier is AITier.DETERMINISTIC
    assert len(text) > 20


@pytest.mark.asyncio
async def test_tier3_is_never_reached_while_a_model_answers(route):
    route(cloud=FakeResponse(200, openai_reply("real")))

    _, tier = await call()

    assert tier is not AITier.DETERMINISTIC


@pytest.mark.asyncio
async def test_degradation_is_logged_loudly(route, caplog):
    # The tier is not in the HTTP response (that would be a D4 change), so the
    # log is the only signal an operator gets that AI is dead.
    route(cloud=None, ollama=None)

    with caplog.at_level(logging.WARNING, logger="app.services.ai_service"):
        await call()

    assert any("AI DEGRADED" in r.getMessage() for r in caplog.records)


@pytest.mark.asyncio
async def test_a_healthy_call_logs_no_warning(route, caplog):
    route(cloud=FakeResponse(200, openai_reply("real")))

    with caplog.at_level(logging.WARNING, logger="app.services.ai_service"):
        await call()

    assert caplog.records == []


@pytest.mark.parametrize("feature", list(AIFeature))
@pytest.mark.asyncio
async def test_tier3_selects_its_answer_by_feature_not_by_prompt_text(route, feature):
    # F-10: the fallback used to sniff substrings out of the prompt, so
    # rewording a prompt silently changed which canned answer came back.
    route(cloud=None, ollama=None)

    text, tier = await AIService._call_llm(feature, "system", "totally unrelated prompt text")

    assert tier is AITier.DETERMINISTIC
    if feature is AIFeature.MEETING_MINUTES:
        assert set(json.loads(text)) >= {"main_topics", "action_items", "key_decisions"}
    elif feature is AIFeature.ASSIGNMENT:
        assert set(json.loads(text)) >= {"recommended_name", "rationale", "risk_assessment"}
    else:
        assert "Tổng quan tiến độ" in text


# --------------------------------------------------------------------------
# What the public methods do with a tier's answer
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_a_real_model_answer_reaches_the_caller_unchanged(route):
    route(cloud=FakeResponse(200, openai_reply("### Genuine weekly analysis")))

    summary = await AIService.generate_weekly_summary([{"id": 1, "title": "t"}])

    # Not the canned Vietnamese report — this is the assertion the old
    # shape-only tests could not make.
    assert summary == "### Genuine weekly analysis"
    assert "Tổng quan tiến độ" not in summary


@pytest.mark.asyncio
async def test_json_fences_are_stripped_from_a_model_answer(route):
    payload = {"main_topics": ["A"], "action_items": [], "key_decisions": ["D"]}
    route(cloud=FakeResponse(200, openai_reply(f"```json\n{json.dumps(payload)}\n```")))

    result = await AIService.extract_meeting_minutes("notes")

    assert result["main_topics"] == ["A"]


@pytest.mark.asyncio
async def test_unparseable_model_json_degrades_to_the_fallback(route, caplog):
    # A model that answers in prose instead of JSON is a degradation too, even
    # though tier 1 "succeeded". The user must still get a usable structure.
    route(cloud=FakeResponse(200, openai_reply("Sure! Here are your minutes: ...")))

    with caplog.at_level(logging.WARNING, logger="app.services.ai_service"):
        result = await AIService.extract_meeting_minutes("notes")

    assert set(result) >= {"main_topics", "action_items", "key_decisions"}
    assert any("unparseable JSON" in r.getMessage() for r in caplog.records)


@pytest.mark.asyncio
async def test_assignment_recommendation_from_a_real_model(route):
    payload = {
        "recommended_user_id": 7,
        "recommended_name": "Ada Lovelace",
        "rationale": "Lowest load",
        "risk_assessment": "None",
    }
    route(cloud=FakeResponse(200, openai_reply(json.dumps(payload))))

    result = await AIService.recommend_task_assignment("t", "d", [{"user_id": 7}])

    assert result["recommended_name"] == "Ada Lovelace"
    # The fallback always names the same hardcoded person; this proves we did
    # not get it.
    assert result["recommended_user_id"] == 7


@pytest.mark.asyncio
async def test_the_endpoint_still_succeeds_when_every_tier_is_down(route, client, pm_auth_headers,
                                                                   project_with_member):
    # The offline zero-failure guarantee (FR-AI-06): degraded, but never a 5xx.
    project_id, _ = project_with_member
    route(cloud=None, ollama=None)

    res = client.post(f"/api/ai/weekly-summary?project_id={project_id}", headers=pm_auth_headers)

    assert res.status_code == 200
    assert len(res.json()["summary"]) > 20
