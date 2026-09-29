"""Tests for configuration parsing, URL normalization, and production safety checks."""

import pytest

from app.config import Settings, normalize_database_url
from app.db import assert_safe_test_db


def test_normalize_database_url_render_schemes():
    # Test postgres:// rewrite
    url = "postgres://user:pass@ep-cool-host.oregon-postgres.render.com/cc_db"
    normalized = normalize_database_url(url)
    assert normalized.startswith("postgresql+psycopg://")
    assert "sslmode=require" in normalized

    # Test postgresql:// rewrite
    url2 = "postgresql://user:pass@ep-cool-host.oregon-postgres.render.com/cc_db"
    normalized2 = normalize_database_url(url2)
    assert normalized2.startswith("postgresql+psycopg://")
    assert "sslmode=require" in normalized2


def test_normalize_database_url_preserves_sqlite():
    sqlite_url = "sqlite:///local_test.db"
    assert normalize_database_url(sqlite_url) == sqlite_url


def test_normalize_database_url_localhost_does_not_force_ssl():
    local_url = "postgresql://postgres:postgres@localhost:5432/controlchaos"
    normalized = normalize_database_url(local_url)
    assert normalized.startswith("postgresql+psycopg://")
    assert "sslmode=require" not in normalized


def test_assert_safe_test_db_blocks_production_render():
    prod_url = "postgresql+psycopg://user:pass@dpg-host.oregon-postgres.render.com/controlchaos_prod?sslmode=require"
    with pytest.raises(RuntimeError, match="REFUSING to execute destructive test setup"):
        assert_safe_test_db(prod_url)


def test_assert_safe_test_db_allows_test_databases():
    # Localhost
    assert_safe_test_db("postgresql+psycopg://user:pass@localhost:5432/test_db")
    # Explicit test in path
    assert_safe_test_db("postgresql+psycopg://user:pass@dpg-host.oregon-postgres.render.com/test_db?sslmode=require")


def test_settings_cors_origins_parsing():
    s = Settings(CORS_ORIGINS="http://localhost:3000, https://app.example.com")
    assert s.cors_origins_list == ["http://localhost:3000", "https://app.example.com"]
