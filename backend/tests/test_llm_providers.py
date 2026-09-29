"""Tests for LLM provider abstraction, MockProvider, and routing logic."""

from app.services.agent.providers import MockProvider, ResilientLLMService, TokenBucketRateLimiter


def test_mock_provider_deterministic_generation():
    provider = MockProvider()

    # Adversary prompt
    resp_adv = provider.generate("Propose campaign", system_prompt="Red Team Adversary Agent")
    assert resp_adv.provider == "mock"
    assert "Mock Adversarial Campaign" in resp_adv.content
    assert resp_adv.parsed_json is not None
    assert "target_classes" in resp_adv.parsed_json

    # Architect prompt
    resp_arch = provider.generate("Propose rule for gap", system_prompt="Control Architect Agent")
    assert "dsl_rule" in resp_arch.parsed_json
    assert resp_arch.parsed_json["target_gap_class"] == "cutoff_error"

    # Skeptic prompt
    resp_skep = provider.generate("Review proposed rule", system_prompt="Skeptic Compliance Reviewer")
    assert resp_skep.parsed_json["verdict"] == "approve_recommend"


def test_token_bucket_limiter():
    limiter = TokenBucketRateLimiter(rpm=600)
    # 5 acquisitions should pass without blocking
    for _ in range(5):
        limiter.acquire()
    assert limiter.tokens < 600


def test_resilient_llm_service_routing():
    service = ResilientLLMService()
    adv_provider = service.get_provider_for_agent("adversary")
    # If GROQ_API_KEY is present in env, adversary routes to groq; otherwise mock
    assert adv_provider.provider_name in ("groq", "mock")

    # Unknown agent falls back cleanly
    unknown_provider = service.get_provider_for_agent("unknown_agent")
    assert unknown_provider.provider_name in ("mock", "groq", "gemini")

    status = service.get_provider_status()
    assert "groq" in status
    assert "gemini" in status
    assert "mock" in status
    assert status["mock"]["configured"] is True
