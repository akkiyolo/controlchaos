"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path
from typing import List, Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(url: str) -> str:
    """
    Normalizes Render and PostgreSQL connection URLs:
    - Replaces 'postgres://' or 'postgresql://' with 'postgresql+psycopg://'
    - Ensures sslmode=require is present for postgresql connections unless disabled or sqlite.
    """
    if not url:
        return url

    parsed = urlparse(url)
    scheme = parsed.scheme.lower()

    if scheme.startswith("sqlite"):
        return url

    if scheme in ("postgres", "postgresql", "postgresql+psycopg", "postgresql+psycopg2"):
        new_scheme = "postgresql+psycopg"
    else:
        new_scheme = scheme

    # Check query params for sslmode
    query_params = parse_qs(parsed.query)
    # If it's a remote host (e.g. render.com or postgres) ensure sslmode=require
    if "localhost" not in parsed.netloc and "127.0.0.1" not in parsed.netloc and "test" not in parsed.path:
        if "sslmode" not in query_params:
            query_params["sslmode"] = ["require"]

    # Reconstruct query string
    new_query = urlencode(query_params, doseq=True)
    normalized = urlunparse((
        new_scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment,
    ))
    return normalized


ROOT_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE_PATH = ROOT_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(ENV_FILE_PATH), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # ---------- App ----------
    APP_ENV: str = Field(default="development")
    APP_NAME: str = Field(default="ControlChaos")
    LOG_LEVEL: str = Field(default="INFO")
    API_PREFIX: str = Field(default="/api/v1")
    CORS_ORIGINS: str = Field(default="http://localhost:8000,http://localhost:5500")

    # ---------- Database ----------
    DATABASE_URL: str = Field(default="postgresql+psycopg://postgres:postgres@localhost:5432/controlchaos")
    TEST_DATABASE_URL: Optional[str] = Field(default=None)
    DB_POOL_SIZE: int = Field(default=5)
    DB_MAX_OVERFLOW: int = Field(default=5)
    DB_POOL_PRE_PING: bool = Field(default=True)

    # ---------- Auth ----------
    JWT_SECRET: str = Field(default="change-me-in-production-min-32-chars-key-12345")
    JWT_ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_MINUTES: int = Field(default=30)
    REFRESH_TOKEN_DAYS: int = Field(default=7)

    # ---------- Audit Log ----------
    AUDIT_HASH_SALT: str = Field(default="controlchaos-audit-salt")

    # ---------- LLM Providers ----------
    LLM_PROVIDER: str = Field(default="mock")
    LLM_TIMEOUT_SECONDS: int = Field(default=60)
    LLM_MAX_RETRIES: int = Field(default=4)

    GROQ_API_KEY: Optional[str] = Field(default="")
    GROQ_BASE_URL: str = Field(default="https://api.groq.com/openai/v1")
    GROQ_MODEL: str = Field(default="llama-3.3-70b-versatile")
    LLM_RPM_LIMIT_GROQ: int = Field(default=25)

    GEMINI_API_KEY: Optional[str] = Field(default="")
    GEMINI_BASE_URL: str = Field(default="https://generativelanguage.googleapis.com/v1beta/openai/")
    GEMINI_MODEL: str = Field(default="gemini-2.5-flash")
    LLM_RPM_LIMIT_GEMINI: int = Field(default=10)

    # Per-Agent Routing
    AGENT_PROVIDER_ADVERSARY: str = Field(default="groq")
    AGENT_PROVIDER_INVESTIGATOR: str = Field(default="groq")
    AGENT_PROVIDER_ARCHITECT: str = Field(default="gemini")
    AGENT_PROVIDER_SKEPTIC: str = Field(default="groq")
    AGENT_PROVIDER_VARIANCE: str = Field(default="gemini")

    # Agent Budgets
    AGENT_MAX_STEPS: int = Field(default=25)
    AGENT_MAX_TOKENS_PER_WORKFLOW: int = Field(default=200000)

    # Demo & Seeding
    SEED_DEMO_USERS: bool = Field(default=True)
    DEMO_ADMIN_EMAIL: str = Field(default="admin@controlchaos.local")
    DEMO_ADMIN_PASSWORD: str = Field(default="ControlChaosAdmin2026!")
    DEFAULT_RANDOM_SEED: int = Field(default=42)

    @field_validator("JWT_SECRET", mode="before")
    @classmethod
    def validate_jwt_secret(cls, v: Optional[str]) -> str:
        if not v or not str(v).strip():
            return "controlchaos-default-dev-secret-key-min-32-chars-long!"
        return str(v).strip()

    @field_validator("AUDIT_HASH_SALT", mode="before")
    @classmethod
    def validate_audit_salt(cls, v: Optional[str]) -> str:
        if not v or not str(v).strip():
            return "controlchaos-audit-default-salt"
        return str(v).strip()

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        return normalize_database_url(v)

    @field_validator("TEST_DATABASE_URL", mode="before")
    @classmethod
    def validate_test_database_url(cls, v: Optional[str]) -> Optional[str]:
        if v:
            return normalize_database_url(v)
        return v

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache()
def get_settings() -> Settings:
    return Settings()
