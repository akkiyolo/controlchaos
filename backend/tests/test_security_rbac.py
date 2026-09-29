"""Tests for password hashing, JWT mechanics, and RBAC / maker-checker guards."""

import pytest
from fastapi import HTTPException

from app.core.rbac import Role, assert_maker_checker, require_roles
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.models.entities import User


def test_password_hashing():
    raw = "SuperSecretPassword123!"
    hashed = get_password_hash(raw)
    assert hashed != raw
    assert verify_password(raw, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_jwt_token_creation_and_decoding():
    data = {"sub": "user-uuid-123", "role": "analyst"}
    token = create_access_token(data)
    decoded = decode_token(token)
    assert decoded["sub"] == "user-uuid-123"
    assert decoded["role"] == "analyst"
    assert decoded["type"] == "access"
    assert "exp" in decoded


def test_jwt_refresh_token():
    data = {"sub": "user-uuid-123"}
    token = create_refresh_token(data)
    decoded = decode_token(token)
    assert decoded["sub"] == "user-uuid-123"
    assert decoded["type"] == "refresh"


def test_maker_checker_assertion():
    # Different maker and checker -> OK
    assert_maker_checker(maker_id="user-1", checker_id="user-2")

    # Same maker and checker -> Must raise HTTPException 400
    with pytest.raises(HTTPException) as exc_info:
        assert_maker_checker(maker_id="user-1", checker_id="user-1")
    assert exc_info.value.status_code == 400
    assert "Maker-checker violation" in exc_info.value.detail


def test_require_roles_allows_admin():
    admin_user = User(id="admin-1", email="admin@test.com", role=Role.ADMIN.value, name="Admin", password_hash="x")
    checker = require_roles(Role.CONTROL_OWNER.value)
    # Admin is granted access regardless
    assert checker(admin_user) == admin_user


def test_require_roles_enforces_allowed():
    analyst_user = User(id="analyst-1", email="a@test.com", role=Role.ANALYST.value, name="Analyst", password_hash="x")
    checker = require_roles(Role.CONTROL_OWNER.value)
    with pytest.raises(HTTPException) as exc_info:
        checker(analyst_user)
    assert exc_info.value.status_code == 403
