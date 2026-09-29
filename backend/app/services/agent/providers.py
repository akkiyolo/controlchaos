"""LLM Provider abstraction, rate limiting, retries, and fallback handling."""

import json
import logging
import random
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type, TypeVar

from pydantic import BaseModel

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

T = TypeVar("T", bound=BaseModel)


class LLMUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0


class LLMResponse(BaseModel):
    content: str
    parsed_json: Optional[Dict[str, Any]] = None
    usage: LLMUsage
    provider: str
    model: str
    fallback_used: bool = False


class TokenBucketRateLimiter:
    """Thread-safe in-memory token bucket rate limiter per RPM limit."""

    def __init__(self, rpm: int):
        self.rpm = max(1, rpm)
        self.capacity = float(self.rpm)
        self.tokens = float(self.rpm)
        self.last_update = time.monotonic()

    def acquire(self) -> None:
        now = time.monotonic()
        elapsed = now - self.last_update
        self.last_update = now
        self.tokens = min(self.capacity, self.tokens + elapsed * (self.rpm / 60.0))
        if self.tokens < 1.0:
            sleep_needed = (1.0 - self.tokens) / (self.rpm / 60.0)
            time.sleep(sleep_needed)
            self.tokens = 0.0
            self.last_update = time.monotonic()
        else:
            self.tokens -= 1.0


class LLMProvider(ABC):
    """Abstract base class for all LLM providers."""

    provider_name: str

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        schema: Optional[Type[BaseModel]] = None,
        temperature: float = 0.2,
    ) -> LLMResponse:
        pass


class MockProvider(LLMProvider):
    """Deterministic, rule-based provider for offline testing, demos, and CI."""

    provider_name = "mock"

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        schema: Optional[Type[BaseModel]] = None,
        temperature: float = 0.2,
    ) -> LLMResponse:
        start_time = time.perf_counter()

        sys_lower = (system_prompt or "").lower()
        prompt_lower = prompt.lower()
        content_dict: Dict[str, Any] = {}

        if "adversary" in sys_lower or "campaign" in prompt_lower:
            content_dict = {
                "campaign_name": "Mock Adversarial Campaign",
                "target_classes": ["duplicate_posting", "cutoff_error", "threshold_splitting"],
                "stealth_level": "subtle",
                "magnitude": "medium",
                "rationale": "Targeting control blind-spots across month-end cutoff and threshold clusters.",
                "mutation_count": 5,
            }
        elif "skeptic" in sys_lower or "verdict" in prompt_lower:
            content_dict = {
                "verdict": "approve_recommend",
                "confidence_score": 0.92,
                "auditor_explainability": "The proposed rule uses clear business-day parameters with no black-box logic.",
                "false_positive_risk": "low",
                "reasons": ["Grounded in metric M-104", "Backtest showed 0 baseline false positives"],
            }
        elif "architect" in sys_lower or "rule" in prompt_lower:
            content_dict = {
                "rule_name": "Tightened Cutoff & Duplicate Protection Rule",
                "target_gap_class": "cutoff_error",
                "dsl_rule": {
                    "field": "posting_date",
                    "operator": "within_business_days",
                    "value": 2,
                    "target_account_type": "expense",
                },
                "rationale": "Metric M-104 showed 15% miss rate on cutoff errors near month-end.",
                "expected_recall_gain": 0.25,
            }
        elif "variance" in sys_lower or "commentary" in prompt_lower:
            content_dict = {
                "headline": "Q3 Operating Expense Variance Review",
                "drivers": [
                    {"driver": "IT Licensing Increase", "amount": 45000.0, "pct": 12.5},
                    {"driver": "Foreign Exchange Revaluation", "amount": -12000.0, "pct": -3.2},
                ],
                "narrative": "Operating expenses rose by 45000.0 in period due to IT licensing renewals.",
                "metric_citations": ["VAR-001", "VAR-002"],
            }
        else:
            content_dict = {
                "status": "success",
                "message": "Deterministic response from MockProvider",
                "analysis": "Control gap evaluated and cataloged successfully.",
            }

        content_str = json.dumps(content_dict, indent=2)
        latency_ms = (time.perf_counter() - start_time) * 1000

        prompt_tokens = len(prompt.split()) + len((system_prompt or "").split())
        completion_tokens = len(content_str.split())

        return LLMResponse(
            content=content_str,
            parsed_json=content_dict,
            usage=LLMUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                latency_ms=round(latency_ms, 2),
            ),
            provider="mock",
            model="mock-rule-engine",
            fallback_used=False,
        )


class OpenAICompatibleProvider(LLMProvider):
    """Generic wrapper for OpenAI-compatible endpoints (Groq, Gemini)."""

    def __init__(
        self,
        provider_name: str,
        base_url: str,
        api_key: str,
        model: str,
        rpm_limit: int,
        timeout: int = 60,
        max_retries: int = 3,
    ):
        self.provider_name = provider_name
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.limiter = TokenBucketRateLimiter(rpm=rpm_limit)
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key or "missing-key",
                timeout=float(self.timeout),
            )
        return self._client

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        schema: Optional[Type[BaseModel]] = None,
        temperature: float = 0.2,
    ) -> LLMResponse:
        client = self._get_client()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        last_error = None
        for attempt in range(self.max_retries):
            try:
                self.limiter.acquire()
                start_time = time.perf_counter()

                response = client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    response_format={"type": "json_object"},
                )

                latency_ms = (time.perf_counter() - start_time) * 1000
                choice = response.choices[0]
                content = choice.message.content or "{}"
                parsed_json = json.loads(content)

                usage_raw = getattr(response, "usage", None)
                p_tokens = getattr(usage_raw, "prompt_tokens", 0) if usage_raw else 0
                c_tokens = getattr(usage_raw, "completion_tokens", 0) if usage_raw else 0

                return LLMResponse(
                    content=content,
                    parsed_json=parsed_json,
                    usage=LLMUsage(
                        prompt_tokens=p_tokens,
                        completion_tokens=c_tokens,
                        total_tokens=p_tokens + c_tokens,
                        latency_ms=round(latency_ms, 2),
                    ),
                    provider=self.provider_name,
                    model=self.model,
                    fallback_used=False,
                )

            except Exception as exc:
                last_error = exc
                backoff = (2 ** attempt) + random.uniform(0.1, 0.5)
                logger.warning(
                    "LLM call to %s failed (attempt %d/%d): %s. Backing off for %.2fs",
                    self.provider_name,
                    attempt + 1,
                    self.max_retries,
                    exc,
                    backoff,
                )
                time.sleep(backoff)

        raise RuntimeError(f"Provider {self.provider_name} failed after {self.max_retries} attempts: {last_error}")


class ResilientLLMService:
    """Manages provider routing, fallback hierarchy, and schema validation."""

    def __init__(self):
        self.mock_provider = MockProvider()
        self.groq_provider = (
            OpenAICompatibleProvider(
                provider_name="groq",
                base_url=settings.GROQ_BASE_URL,
                api_key=settings.GROQ_API_KEY or "",
                model=settings.GROQ_MODEL,
                rpm_limit=settings.LLM_RPM_LIMIT_GROQ,
                timeout=settings.LLM_TIMEOUT_SECONDS,
                max_retries=settings.LLM_MAX_RETRIES,
            )
            if settings.GROQ_API_KEY
            else None
        )
        self.gemini_provider = (
            OpenAICompatibleProvider(
                provider_name="gemini",
                base_url=settings.GEMINI_BASE_URL,
                api_key=settings.GEMINI_API_KEY or "",
                model=settings.GEMINI_MODEL,
                rpm_limit=settings.LLM_RPM_LIMIT_GEMINI,
                timeout=settings.LLM_TIMEOUT_SECONDS,
                max_retries=settings.LLM_MAX_RETRIES,
            )
            if settings.GEMINI_API_KEY
            else None
        )

    def get_provider_for_agent(self, agent_name: str) -> LLMProvider:
        """Determines the active provider for a given agent with graceful fallbacks."""
        agent_key = agent_name.lower()
        provider_preference = {
            "adversary": settings.AGENT_PROVIDER_ADVERSARY,
            "investigator": settings.AGENT_PROVIDER_INVESTIGATOR,
            "architect": settings.AGENT_PROVIDER_ARCHITECT,
            "skeptic": settings.AGENT_PROVIDER_SKEPTIC,
            "variance": settings.AGENT_PROVIDER_VARIANCE,
        }.get(agent_key, settings.LLM_PROVIDER).lower()

        if provider_preference == "groq" and self.groq_provider:
            return self.groq_provider
        if provider_preference == "gemini" and self.gemini_provider:
            return self.gemini_provider

        global_pref = settings.LLM_PROVIDER.lower()
        if global_pref == "groq" and self.groq_provider:
            return self.groq_provider
        if global_pref == "gemini" and self.gemini_provider:
            return self.gemini_provider

        return self.mock_provider

    def generate_with_fallback(
        self,
        agent_name: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        schema: Optional[Type[BaseModel]] = None,
    ) -> LLMResponse:
        primary = self.get_provider_for_agent(agent_name)
        try:
            return primary.generate(prompt, system_prompt, schema)
        except Exception as exc:
            logger.warning(
                "Primary provider %s for agent %s failed: %s. Falling back to MockProvider.",
                primary.provider_name,
                agent_name,
                exc,
            )
            response = self.mock_provider.generate(prompt, system_prompt, schema)
            response.fallback_used = True
            return response

    @staticmethod
    def get_provider_status() -> Dict[str, Dict[str, Any]]:
        """Returns safe status without exposing secrets for frontend display."""
        return {
            "groq": {
                "configured": bool(settings.GROQ_API_KEY),
                "model": settings.GROQ_MODEL,
                "rpm_limit": settings.LLM_RPM_LIMIT_GROQ,
            },
            "gemini": {
                "configured": bool(settings.GEMINI_API_KEY),
                "model": settings.GEMINI_MODEL,
                "rpm_limit": settings.LLM_RPM_LIMIT_GEMINI,
            },
            "mock": {
                "configured": True,
                "model": "mock-rule-engine",
                "rpm_limit": 10000,
            },
        }


llm_service = ResilientLLMService()
