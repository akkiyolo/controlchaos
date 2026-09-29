# ControlChaos Architecture & Design Decisions

This document records architectural, design, and technical decisions made during development.

## Decision 1: Database URL Scheme and Normalization
- **Context:** Render external database connection strings typically start with `postgres://` or `postgresql://`. SQLAlchemy 2.0 with the modern `psycopg` (v3) driver requires the `postgresql+psycopg://` dialect scheme, and Render requires `sslmode=require`.
- **Decision:** Auto-normalize incoming database URLs in `backend/app/config.py` using `normalize_database_url()`. If a remote host URL lacks `sslmode`, automatically inject `sslmode=require`. Alembic and the application share the identical normalized URL.

## Decision 2: Production Database Protection Guardrail
- **Context:** Automated tests running destructive operations (e.g., dropping or resetting tables) must never run against production Render databases.
- **Decision:** Provide an explicit `assert_safe_test_db(url)` check and test fixtures that prevent running tests if `DATABASE_URL` matches a remote Render host without explicit test designation.

## Decision 3: Cryptographic Audit Chain Mechanics
- **Context:** Financial compliance and governance require a tamper-evident audit log.
- **Decision:** Each audit entry calculates `hash = SHA256(prev_hash || canonical_json(record) || AUDIT_HASH_SALT)`. Canonical JSON sorts all keys deterministically with compact whitespace separators (`","` and `":"`). Chain verification is exposed via `GET /api/v1/audit/verify` and verified end-to-end.

## Decision 4: LLM Provider Abstraction and Multi-Agent Routing
- **Context:** The system must run completely offline without API keys in CI/demos (using `MockProvider`), while supporting high-throughput production execution with Groq and Google Gemini via OpenAI-compatible endpoints.
- **Decision:** `ResilientLLMService` handles token-bucket rate limiting per provider, retries with exponential backoff on 429/5xx, and automatic fallbacks (Groq/Gemini -> Secondary -> MockProvider). Model diversity is enforced: Control Architect defaults to Gemini and Skeptic defaults to Groq to prevent shared blind spots.

## Decision 5: Frontend Architecture (No-Build Vanilla ES Modules)
- **Context:** Web application needs to feel like a high-end Tier 1 financial terminal (Bloomberg/FactSet aesthetic), supporting dark/light mode, tabular numerals, responsive layout, and role-based workflows without React/Node build steps.
- **Decision:** Vanilla HTML5, modern CSS custom properties with HSL color system, and modular ES6 JavaScript (`api.js`, `router.js`, `store.js`, page components) served statically by FastAPI.
